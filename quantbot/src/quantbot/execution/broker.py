"""Broker 추상화 — LiveEngine이 KIS JSON 세부사항에 의존하지 않도록 분리.

  - Broker: 실행 계층이 만족해야 하는 최소 인터페이스 (Protocol).
  - KISBroker: KISClient를 감싸 KIS 응답을 깔끔한 타입으로 변환하는 어댑터.
  - DryRunBroker: 네트워크 없이 도는 모의 브로커 (오프라인 스모크/테스트용).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..market import round_to_tick


@dataclass(frozen=True)
class Position:
    ticker: str
    qty: int
    avg_price: float

    @property
    def value(self) -> float:
        return self.qty * self.avg_price


@dataclass
class AccountSnapshot:
    total_equity: float          # 총평가금액
    cash: float                  # 주문 가능 현금 (예수금)
    positions: dict[str, Position] = field(default_factory=dict)

    def held(self, ticker: str) -> bool:
        pos = self.positions.get(ticker)
        return pos is not None and pos.qty > 0


@runtime_checkable
class Broker(Protocol):
    """실행 계층 인터페이스. 시장가 주문만 노출한다 (price=0)."""

    def current_price(self, ticker: str) -> float: ...
    def today_open(self, ticker: str) -> float: ...
    def snapshot(self) -> AccountSnapshot: ...
    def buy(self, ticker: str, qty: int) -> None: ...
    def sell(self, ticker: str, qty: int) -> None: ...


class KISBroker:
    """KISClient → Broker 어댑터. KIS 응답 필드명을 여기서만 다룬다."""

    def __init__(self, client) -> None:  # client: KISClient (순환 import 방지)
        self._client = client

    def current_price(self, ticker: str) -> float:
        return float(self._client.current_price(ticker)["stck_prpr"])

    def today_open(self, ticker: str) -> float:
        return float(self._client.current_price(ticker)["stck_oprc"])

    def snapshot(self) -> AccountSnapshot:
        data = self._client.balance()
        summary = data["output2"][0]
        positions: dict[str, Position] = {}
        for h in data["output1"]:
            qty = int(h["hldg_qty"])
            if qty > 0:
                positions[h["pdno"]] = Position(
                    ticker=h["pdno"],
                    qty=qty,
                    avg_price=float(h["pchs_avg_pric"]),
                )
        return AccountSnapshot(
            total_equity=float(summary["tot_evlu_amt"]),
            cash=float(summary["dnca_tot_amt"]),  # 예수금총금액
            positions=positions,
        )

    def buy(self, ticker: str, qty: int) -> None:
        self._client.order_cash(ticker, qty, "buy", price=0)  # 시장가

    def sell(self, ticker: str, qty: int) -> None:
        self._client.order_cash(ticker, qty, "sell", price=0)


class DryRunBroker:
    """네트워크 없이 도는 모의 브로커.

    주문은 현재가(시장가 가정)로 즉시 체결된다. 수수료/세금은 실행 루프
    검증이 목적이므로 반영하지 않는다(정확한 비용 반영은 백테스트 엔진 담당).
    """

    def __init__(
        self,
        cash: float,
        prices: dict[str, float],
        opens: dict[str, float] | None = None,
    ) -> None:
        self._cash = cash
        self._prices = dict(prices)
        self._opens = dict(opens or prices)
        self._positions: dict[str, Position] = {}
        self.fills: list[tuple[str, str, int, float]] = []  # (side, ticker, qty, price)

    # --- 시세 주입 (모의 장중 가격 변화) --------------------------------
    def set_price(self, ticker: str, price: float) -> None:
        self._prices[ticker] = price

    # --- Broker 인터페이스 ----------------------------------------------
    def current_price(self, ticker: str) -> float:
        return self._prices[ticker]

    def today_open(self, ticker: str) -> float:
        return self._opens[ticker]

    def snapshot(self) -> AccountSnapshot:
        equity = self._cash + sum(
            p.qty * self._prices[t] for t, p in self._positions.items()
        )
        return AccountSnapshot(
            total_equity=equity,
            cash=self._cash,
            positions=dict(self._positions),
        )

    def buy(self, ticker: str, qty: int) -> None:
        price = float(round_to_tick(self._prices[ticker], "up"))
        cost = price * qty
        if cost > self._cash:
            raise RuntimeError("모의 현금 부족")
        prev = self._positions.get(ticker)
        new_qty = (prev.qty if prev else 0) + qty
        prev_value = prev.value if prev else 0.0
        self._positions[ticker] = Position(
            ticker, new_qty, (prev_value + cost) / new_qty
        )
        self._cash -= cost
        self.fills.append(("buy", ticker, qty, price))

    def sell(self, ticker: str, qty: int) -> None:
        pos = self._positions.get(ticker)
        if not pos or pos.qty < qty:
            raise RuntimeError("모의 보유 수량 부족")
        price = float(round_to_tick(self._prices[ticker], "down"))
        self._cash += price * qty
        remaining = pos.qty - qty
        if remaining:
            self._positions[ticker] = Position(ticker, remaining, pos.avg_price)
        else:
            del self._positions[ticker]
        self.fills.append(("sell", ticker, qty, price))
