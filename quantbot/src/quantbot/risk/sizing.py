"""포지션 사이징 — 고정비율, Kelly의 분수."""

from __future__ import annotations


def fixed_fraction(equity: float, price: float, fraction: float = 0.10) -> int:
    """계좌의 fraction 만큼 매수할 수량."""
    if price <= 0 or not 0 < fraction <= 1:
        return 0
    return int(equity * fraction // price)


def kelly_fraction(
    win_rate: float, avg_win: float, avg_loss: float, scale: float = 0.25
) -> float:
    """Kelly 비중 × scale (기본 1/4 Kelly). 음수면 0 (베팅 금지).

    avg_win/avg_loss는 1회 트레이드 평균 손익률 (avg_loss는 양수로).
    """
    if avg_loss <= 0 or avg_win <= 0 or not 0 <= win_rate <= 1:
        return 0.0
    b = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / b
    return max(0.0, kelly * scale)
