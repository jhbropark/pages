"""과최적화 방지 — walk-forward 검증.

train 구간에서 파라미터를 고르고, 바로 뒤 test 구간에서만 성과를 인정한다.
전 구간 최적화 결과는 참고용일 뿐, OOS(out-of-sample) 성과가 진짜다.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pandas as pd

from ..config import CostConfig
from ..strategy.base import Strategy
from .engine import run_backtest
from .metrics import sharpe, summarize


def split_windows(
    df: pd.DataFrame, train_size: int, test_size: int
) -> Iterator[tuple[pd.DataFrame, pd.DataFrame]]:
    """롤링 (train, test) 윈도우. 크기는 거래일 수 기준."""
    start = 0
    while start + train_size + test_size <= len(df):
        train = df.iloc[start : start + train_size]
        test = df.iloc[start + train_size : start + train_size + test_size]
        yield train, test
        start += test_size


def run_walk_forward(
    df: pd.DataFrame,
    strategy_factory: Callable[..., Strategy],
    param_grid: list[dict],
    train_size: int = 504,   # ~2년
    test_size: int = 126,    # ~6개월
    initial_cash: float = 10_000_000,
    costs: CostConfig | None = None,
) -> dict:
    """각 윈도우: train에서 Sharpe 최대 파라미터 선택 → test 성과 연결.

    반환: {"oos_equity": Series, "windows": [윈도우별 선택 파라미터/성과], "summary": dict}
    """
    windows = []
    oos_parts: list[pd.Series] = []
    cash = initial_cash

    for train, test in split_windows(df, train_size, test_size):
        best_params, best_score = None, float("-inf")
        for params in param_grid:
            result = run_backtest(train, strategy_factory(**params), cash, costs)
            score = sharpe(result.equity)
            if score > best_score:
                best_params, best_score = params, score

        assert best_params is not None
        # 전략 warmup을 위해 train 꼬리를 붙이되, 성과는 test 구간만 집계
        warmup = strategy_factory(**best_params).warmup
        seeded = pd.concat([train.iloc[-warmup:], test])
        result = run_backtest(seeded, strategy_factory(**best_params), cash, costs)
        test_equity = result.equity.loc[test.index[0] :]

        windows.append(
            {
                "train": (str(train.index[0].date()), str(train.index[-1].date())),
                "test": (str(test.index[0].date()), str(test.index[-1].date())),
                "params": best_params,
                "train_sharpe": best_score,
                "test_sharpe": sharpe(test_equity),
            }
        )
        oos_parts.append(test_equity)
        if len(test_equity):
            cash = float(test_equity.iloc[-1])  # 다음 윈도우로 자본 이월

    oos_equity = pd.concat(oos_parts) if oos_parts else pd.Series(dtype=float)
    return {
        "oos_equity": oos_equity,
        "windows": windows,
        "summary": summarize(oos_equity) if len(oos_equity) else {},
    }
