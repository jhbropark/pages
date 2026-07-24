"""LiveEngine — 전략·리스크·실행·알림을 잇는 장중 실행 오케스트레이터.

하루 생애주기 (스케줄러가 호출):
  open_session()   장 시작: 계좌 스냅샷 → 리스크 데이 시작 → 전략 계획 수립
                   → 시가 주문(청산 먼저) 실행. stop/종가 주문은 대기열로.
  poll()           장중 반복: 대기 stop 주문의 트리거 여부 확인·체결.
                   일일 손실 한도 도달 시 신규 매수 차단.
  close_session()  장 마감: 종가 주문 실행 → 일일 결산 알림.

시점 규약은 백테스트와 동일: 전략은 t-1까지의 일봉 + 당일 시가만 본다.
백테스트에서 검증한 전략을 그대로 실전에 태우기 위한 얇은 어댑터다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import pandas as pd

from ..execution.broker import AccountSnapshot, Broker, Position
from ..notify.telegram import TelegramNotifier
from ..risk.manager import RiskManager
from ..strategy.base import Order, Strategy

log = logging.getLogger(__name__)

HistoryProvider = Callable[[str], pd.DataFrame]


class LiveEngine:
    def __init__(
        self,
        broker: Broker,
        strategies: dict[str, Strategy],
        risk: RiskManager,
        notifier: TelegramNotifier,
        history_provider: HistoryProvider,
    ) -> None:
        self.broker = broker
        self.strategies = strategies
        self.risk = risk
        self.notifier = notifier
        self.history_provider = history_provider
        # 종목별 미체결 stop/종가 주문 대기열
        self._pending: dict[str, list[Order]] = {}
        self._snapshot: AccountSnapshot | None = None

    # --- 세션 생애주기 ---------------------------------------------------
    def open_session(self) -> None:
        snap = self.broker.snapshot()
        self._snapshot = snap
        self.risk.start_day(snap.total_equity)
        self._pending = {}
        log.info("장 시작 — 평가금액 %s원, 보유 %d종목", f"{snap.total_equity:,.0f}", len(snap.positions))

        for ticker, strat in self.strategies.items():
            try:
                history = self.history_provider(ticker)
                today_open = self.broker.today_open(ticker)
            except Exception as e:  # 시세/데이터 조회 실패는 해당 종목만 건너뜀
                self.risk.record_api_error()
                self.notifier.error(f"{ticker} 시세/데이터 조회 실패: {e}")
                continue
            self.risk.record_api_success()

            orders = strat.on_bar(history, today_open, snap.held(ticker))
            immediate = [o for o in orders if o.kind == "open"]
            deferred = [o for o in orders if o.kind in ("stop", "close")]
            # 청산(시가 매도)을 먼저 실행해 당일 현금을 회전에 재사용
            for order in sorted(immediate, key=lambda o: o.side != "sell"):
                self._execute(ticker, order, self.broker.today_open(ticker))
            if deferred:
                self._pending[ticker] = deferred

    def poll(self) -> None:
        """장중 1회 폴링 — stop 주문 트리거 확인. 스케줄러가 주기적으로 호출."""
        if self._snapshot is None:
            return
        equity = self.broker.snapshot().total_equity
        if self.risk.daily_loss_exceeded(equity) and not self.risk.killed:
            self.risk.kill("일일 손실 한도 도달 — 장중 신규 진입 중단")
            self.notifier.error(self.risk.kill_reason)

        for ticker, orders in list(self._pending.items()):
            remaining: list[Order] = []
            for order in orders:
                if order.kind == "close":
                    remaining.append(order)  # 종가 주문은 마감에 처리
                    continue
                price = self.broker.current_price(ticker)
                if self._stop_triggered(order, price):
                    self._execute(ticker, order, price)
                else:
                    remaining.append(order)
            if remaining:
                self._pending[ticker] = remaining
            else:
                del self._pending[ticker]

    def close_session(self) -> None:
        for ticker, orders in list(self._pending.items()):
            for order in orders:
                if order.kind == "close":
                    self._execute(ticker, order, self.broker.current_price(ticker))
            # 미트리거 stop 주문은 백테스트와 동일하게 당일 만료(폐기)
        self._pending = {}
        self._daily_report()

    # --- 체결 판정/실행 --------------------------------------------------
    @staticmethod
    def _stop_triggered(order: Order, price: float) -> bool:
        assert order.stop_price is not None
        if order.side == "buy":
            return price >= order.stop_price  # 목표가 상향 돌파 시 매수
        return price <= order.stop_price      # 손절가 하향 이탈 시 매도

    def _execute(self, ticker: str, order: Order, price: float) -> None:
        if order.side == "sell":
            self._execute_sell(ticker, price)
        else:
            self._execute_buy(ticker, order, price)

    def _execute_sell(self, ticker: str, price: float) -> None:
        assert self._snapshot is not None
        pos = self._snapshot.positions.get(ticker)
        if not pos or pos.qty <= 0:
            return
        try:
            self.broker.sell(ticker, pos.qty)
            self.risk.record_api_success()
        except Exception as e:
            self.risk.record_api_error()
            self.notifier.error(f"{ticker} 매도 실패: {e}")
            return
        self.notifier.fill("sell", ticker, pos.qty, price)
        self._snapshot.cash += pos.qty * price
        del self._snapshot.positions[ticker]

    def _execute_buy(self, ticker: str, order: Order, price: float) -> None:
        assert self._snapshot is not None
        snap = self._snapshot
        qty = self._target_buy_qty(ticker, price, order)
        if qty <= 0:
            return
        pos = snap.positions.get(ticker)
        position_value = pos.value if pos else 0.0
        ok, reason = self.risk.can_buy(
            snap.total_equity, qty * price, position_value, len(snap.positions)
        )
        if not ok:
            log.info("매수 거부 %s: %s", ticker, reason)
            return
        try:
            self.broker.buy(ticker, qty)
            self.risk.record_api_success()
        except Exception as e:
            self.risk.record_api_error()
            self.notifier.error(f"{ticker} 매수 실패: {e}")
            return
        self.notifier.fill("buy", ticker, qty, price)
        snap.cash -= qty * price
        new_qty = (pos.qty if pos else 0) + qty
        snap.positions[ticker] = Position(ticker, new_qty, price)

    def _target_buy_qty(self, ticker: str, price: float, order: Order) -> int:
        """전략 weight와 리스크 비중 한도 중 작은 쪽으로 수량 산정."""
        assert self._snapshot is not None
        snap = self._snapshot
        if price <= 0:
            return 0
        pos = snap.positions.get(ticker)
        existing_value = pos.value if pos else 0.0
        weight_budget = snap.cash * order.weight
        cap_budget = self.risk.config.max_position_weight * snap.total_equity - existing_value
        budget = min(weight_budget, cap_budget, snap.cash)
        return int(budget // price) if budget > 0 else 0

    # --- 결산 ------------------------------------------------------------
    def _daily_report(self) -> None:
        equity = self.broker.snapshot().total_equity
        start = self.risk.day_start_equity
        pnl = equity - start
        pnl_pct = pnl / start if start > 0 else 0.0
        self.notifier.daily_report(equity, pnl, pnl_pct)
