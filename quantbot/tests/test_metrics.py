import numpy as np
import pandas as pd
import pytest

from quantbot.backtest.metrics import (
    TRADING_DAYS,
    cagr,
    max_drawdown,
    profit_factor,
    sharpe,
    summarize,
    win_rate,
)


def test_cagr_one_year_double():
    dates = pd.bdate_range("2025-01-02", periods=TRADING_DAYS)
    equity = pd.Series(np.linspace(100, 200, TRADING_DAYS), index=dates)
    assert cagr(equity) == pytest.approx(1.0, abs=0.01)


def test_max_drawdown():
    equity = pd.Series([100, 120, 90, 110, 80])
    # 고점 120 → 저점 80: -33.3%
    assert max_drawdown(equity) == pytest.approx(-1 / 3, abs=1e-9)


def test_sharpe_zero_vol():
    equity = pd.Series([100.0, 100.0, 100.0])
    assert sharpe(equity) == 0.0


def test_win_rate_and_profit_factor():
    pnls = pd.Series([100, -50, 200, -50])
    assert win_rate(pnls) == 0.5
    assert profit_factor(pnls) == pytest.approx(3.0)


def test_summarize_includes_trade_stats():
    dates = pd.bdate_range("2025-01-02", periods=10)
    equity = pd.Series(np.linspace(100, 110, 10), index=dates)
    trades = pd.DataFrame({"pnl": [5.0, -2.0, 7.0]})
    out = summarize(equity, trades)
    assert out["num_trades"] == 3
    assert out["win_rate"] == pytest.approx(2 / 3)
    assert out["total_return"] == pytest.approx(0.10)
