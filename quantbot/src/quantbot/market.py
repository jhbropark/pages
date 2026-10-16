"""KRX market microstructure rules shared by backtest and live execution."""

from __future__ import annotations

PRICE_LIMIT_RATE = 0.30  # 상/하한가 ±30%

# 2023-01-25 개편 이후 KRX 호가단위 (코스피/코스닥 공통)
_TICK_TABLE = (
    (2_000, 1),
    (5_000, 5),
    (20_000, 10),
    (50_000, 50),
    (200_000, 100),
    (500_000, 500),
    (float("inf"), 1_000),
)


def tick_size(price: float) -> int:
    """호가단위. price는 원 단위."""
    for upper, tick in _TICK_TABLE:
        if price < upper:
            return tick
    raise AssertionError("unreachable")


def round_to_tick(price: float, direction: str = "down") -> int:
    """가격을 호가단위에 맞춰 절사/절상.

    direction: "down"(매도 지정가 등 보수적) | "up" | "nearest"
    """
    tick = tick_size(price)
    if direction == "down":
        return int(price // tick) * tick
    if direction == "up":
        return int(-(-price // tick)) * tick
    return int(round(price / tick)) * tick


def upper_limit(prev_close: float) -> int:
    """상한가 (호가단위 절사)."""
    return round_to_tick(prev_close * (1 + PRICE_LIMIT_RATE), "down")


def lower_limit(prev_close: float) -> int:
    """하한가 (호가단위 절상)."""
    return round_to_tick(prev_close * (1 - PRICE_LIMIT_RATE), "up")


def is_limit_up(price: float, prev_close: float) -> bool:
    return price >= upper_limit(prev_close)


def is_limit_down(price: float, prev_close: float) -> bool:
    return price <= lower_limit(prev_close)
