"""래리 윌리엄스 변동성 돌파.

매일: 목표가 = 당일 시가 + k × (전일 고가 - 전일 저가).
장중 목표가 돌파 시 매수, 다음 날 시가 전량 매도.
"""

from __future__ import annotations

import pandas as pd

from .base import Order, Strategy


class VolatilityBreakout(Strategy):
    warmup = 2

    def __init__(self, k: float = 0.5, weight: float = 1.0):
        if not 0 < k <= 1:
            raise ValueError("k는 (0, 1] 범위가 일반적입니다")
        self.k = k
        self.weight = weight

    def on_bar(
        self, history: pd.DataFrame, today_open: float, holding: bool
    ) -> list[Order]:
        orders: list[Order] = []
        # 전일 진입분은 오늘 시가에 청산
        if holding:
            orders.append(Order(side="sell", kind="open"))
        prev = history.iloc[-1]
        prev_range = float(prev["high"] - prev["low"])
        target = today_open + self.k * prev_range
        if prev_range > 0:
            orders.append(
                Order(side="buy", kind="stop", stop_price=target, weight=self.weight)
            )
        return orders
