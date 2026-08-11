"""Strategy interface for the event-driven daily backtest engine.

시점 규약 (lookahead 방지):
  거래일 t에 전략이 보는 정보 = t-1까지의 완성된 봉 전체 + t의 시가.
  전략은 t에 실행할 주문 목록을 반환하고, 엔진이 t 봉으로 체결을 판정한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import pandas as pd

OrderKind = Literal["open", "close", "stop"]
Side = Literal["buy", "sell"]


@dataclass(frozen=True)
class Order:
    """단일 종목 주문 의도.

    kind:
      "open"  시가 시장가 체결
      "close" 종가 시장가 체결
      "stop"  stop_price 이상(매수)/이하(매도) 도달 시 체결
    weight: 매수 시 가용 자본 대비 투입 비율 (매도는 전량 청산)
    """

    side: Side
    kind: OrderKind
    stop_price: float | None = None
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.kind == "stop" and self.stop_price is None:
            raise ValueError("stop 주문은 stop_price가 필요합니다")
        if not 0 < self.weight <= 1:
            raise ValueError("weight는 (0, 1] 범위")


class Strategy(ABC):
    """전략은 상태를 갖지 않는 것을 권장 — 재현성과 walk-forward가 쉬워진다."""

    #: 신호 계산에 필요한 최소 과거 봉 수. 엔진이 이 구간은 건너뛴다.
    warmup: int = 1

    @abstractmethod
    def on_bar(
        self, history: pd.DataFrame, today_open: float, holding: bool
    ) -> list[Order]:
        """history: t-1까지의 OHLCV. 반환: 거래일 t의 주문 목록."""
        raise NotImplementedError
