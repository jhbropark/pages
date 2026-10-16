"""단일 종목 이벤트 방식 일봉 백테스트 엔진.

반영하는 한국 시장 특수성:
  - 수수료(매수/매도), 증권거래세(매도), 슬리피지
  - 호가단위 반올림
  - 상/하한가 잠김(고가==저가==상하한가) 시 체결 불가
  - 거래정지일(거래량 0) 체결 불가
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..config import CostConfig
from ..market import is_limit_down, is_limit_up, round_to_tick
from ..strategy.base import Order, Strategy


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    qty: int
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    pnl: float = 0.0


@dataclass
class BacktestResult:
    equity: pd.Series  # 일별 평가금액 (종가 기준)
    trades: list[Trade] = field(default_factory=list)

    @property
    def trades_df(self) -> pd.DataFrame:
        return pd.DataFrame([t.__dict__ for t in self.trades])


def _locked_limit(bar: pd.Series, prev_close: float, side: str) -> bool:
    """상/하한가에 하루 종일 잠겨 반대 방향 체결이 불가능한 봉인지."""
    if bar["high"] != bar["low"]:
        return False
    if side == "buy":
        return is_limit_up(bar["high"], prev_close)
    return is_limit_down(bar["low"], prev_close)


def run_backtest(
    df: pd.DataFrame,
    strategy: Strategy,
    initial_cash: float = 10_000_000,
    costs: CostConfig | None = None,
) -> BacktestResult:
    costs = costs or CostConfig()
    cash = initial_cash
    qty = 0
    entry_trade: Trade | None = None
    trades: list[Trade] = []
    equity_curve: dict[pd.Timestamp, float] = {}

    def buy_cost(price: float) -> float:
        return price * (1 + costs.slippage_rate) * (1 + costs.commission_rate)

    def sell_proceeds(price: float) -> float:
        return (
            price
            * (1 - costs.slippage_rate)
            * (1 - costs.commission_rate - costs.sell_tax_rate)
        )

    for t in range(strategy.warmup, len(df)):
        bar = df.iloc[t]
        date = df.index[t]
        prev_close = float(df["close"].iloc[t - 1])
        halted = bar["volume"] == 0

        orders = strategy.on_bar(df.iloc[:t], float(bar["open"]), qty > 0)

        # 매도 먼저 처리해 당일 자금 재사용(회전)을 허용
        for order in sorted(orders, key=lambda o: o.side != "sell"):
            if halted:
                continue
            if order.side == "sell" and qty > 0:
                if _locked_limit(bar, prev_close, "sell"):
                    continue  # 하한가 잠김 — 다음 날로 이월 (전략이 재시도)
                if order.kind == "open":
                    px = float(bar["open"])
                elif order.kind == "close":
                    px = float(bar["close"])
                else:  # stop sell
                    if float(bar["low"]) > order.stop_price:
                        continue
                    px = min(float(bar["open"]), order.stop_price)
                px = float(round_to_tick(px, "down"))
                proceeds = sell_proceeds(px) * qty
                cash += proceeds
                assert entry_trade is not None
                entry_trade.exit_date = date
                entry_trade.exit_price = px
                entry_trade.pnl = proceeds - buy_cost(entry_trade.entry_price) * qty
                qty = 0
                entry_trade = None

            elif order.side == "buy" and qty == 0:
                if _locked_limit(bar, prev_close, "buy"):
                    continue  # 상한가 잠김 — 매수 불가
                if order.kind == "open":
                    px = float(bar["open"])
                elif order.kind == "close":
                    px = float(bar["close"])
                else:  # stop buy: 장중 목표가 돌파 시
                    if float(bar["high"]) < order.stop_price:
                        continue
                    px = max(float(bar["open"]), order.stop_price)
                px = float(round_to_tick(px, "up"))
                budget = cash * order.weight
                fill_qty = int(budget // buy_cost(px))
                if fill_qty <= 0:
                    continue
                cash -= buy_cost(px) * fill_qty
                qty = fill_qty
                entry_trade = Trade(entry_date=date, entry_price=px, qty=fill_qty)
                trades.append(entry_trade)

        equity_curve[date] = cash + qty * float(bar["close"])

    # 마지막 날까지 미청산 포지션은 종가 청산으로 평가
    if entry_trade is not None and entry_trade.exit_date is None:
        last = df.iloc[-1]
        px = float(round_to_tick(float(last["close"]), "down"))
        entry_trade.exit_date = df.index[-1]
        entry_trade.exit_price = px
        entry_trade.pnl = (
            sell_proceeds(px) - buy_cost(entry_trade.entry_price)
        ) * entry_trade.qty

    return BacktestResult(equity=pd.Series(equity_curve, name="equity"), trades=trades)
