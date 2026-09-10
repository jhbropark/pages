"""볼린저 밴드 + RSI 평균회귀.

전일 종가가 하단 밴드 아래이고 RSI가 과매도면 오늘 시가 매수,
중심선(이동평균) 회복 또는 보유일 한도 도달 시 시가 매도.
"""

from __future__ import annotations

import pandas as pd

from .base import Order, Strategy


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, min_periods=period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return (100 - 100 / (1 + rs)).fillna(100.0)


class BollingerReversion(Strategy):
    def __init__(
        self,
        window: int = 20,
        num_std: float = 2.0,
        rsi_period: int = 14,
        rsi_buy: float = 30.0,
        max_hold_days: int = 10,
        weight: float = 1.0,
    ):
        self.window = window
        self.num_std = num_std
        self.rsi_period = rsi_period
        self.rsi_buy = rsi_buy
        self.max_hold_days = max_hold_days
        self.weight = weight
        self.warmup = max(window, rsi_period) + 1
        self._held_days = 0  # 엔진이 단일 포지션만 지원하므로 여기서만 상태 유지

    def on_bar(
        self, history: pd.DataFrame, today_open: float, holding: bool
    ) -> list[Order]:
        close = history["close"]
        ma = float(close.rolling(self.window).mean().iloc[-1])
        std = float(close.rolling(self.window).std().iloc[-1])
        last_close = float(close.iloc[-1])

        if holding:
            self._held_days += 1
            if last_close >= ma or self._held_days >= self.max_hold_days:
                self._held_days = 0
                return [Order(side="sell", kind="open")]
            return []

        self._held_days = 0
        lower_band = ma - self.num_std * std
        oversold = float(rsi(close, self.rsi_period).iloc[-1]) <= self.rsi_buy
        if last_close < lower_band and oversold:
            return [Order(side="buy", kind="open", weight=self.weight)]
        return []
