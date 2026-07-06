import numpy as np
import pandas as pd

from quantbot.backtest.engine import run_backtest
from quantbot.backtest.walkforward import run_walk_forward, split_windows
from quantbot.config import CostConfig
from quantbot.strategy.dual_momentum import backtest_monthly, momentum_weights
from quantbot.strategy.mean_reversion import BollingerReversion, rsi
from quantbot.strategy.volatility_breakout import VolatilityBreakout


def test_volatility_breakout_buy_and_next_open_sell():
    # 전일 range 1,000 × k=0.5 → 목표가 = 시가 + 500
    df = pd.DataFrame(
        {
            "open": [10_000, 10_000, 10_000, 10_500],
            "high": [11_000, 10_200, 10_800, 10_600],
            "low": [10_000, 9_900, 9_950, 10_300],
            "close": [10_500, 10_000, 10_600, 10_400],
            "volume": [1000] * 4,
        },
        index=pd.bdate_range("2025-01-02", periods=4),
    )
    result = run_backtest(
        df,
        VolatilityBreakout(k=0.5),
        10_000_000,
        CostConfig(commission_rate=0, sell_tax_rate=0, slippage_rate=0),
    )
    # 3일째: 목표 10,000+0.5×300=10,150 → 고가 10,800 도달, 진입
    # 4일째: 시가 10,500 청산
    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 10_150
    assert result.trades[0].exit_price == 10_500


def test_volatility_breakout_runs_on_synthetic(synthetic_ohlcv):
    result = run_backtest(synthetic_ohlcv, VolatilityBreakout(k=0.5), 10_000_000)
    assert len(result.trades) > 10  # 250일이면 다수 체결 기대
    assert (result.equity > 0).all()


def test_rsi_bounds(synthetic_ohlcv):
    values = rsi(synthetic_ohlcv["close"]).dropna()
    assert ((values >= 0) & (values <= 100)).all()


def test_mean_reversion_runs(synthetic_ohlcv):
    result = run_backtest(synthetic_ohlcv, BollingerReversion(), 10_000_000)
    for t in result.trades:
        if t.exit_date is not None:
            held = (t.exit_date - t.entry_date).days
            assert held <= 20  # max_hold_days=10 거래일 ≈ 달력 14일 + 여유


def test_walkforward_oos_continuity(synthetic_ohlcv):
    out = run_walk_forward(
        synthetic_ohlcv,
        VolatilityBreakout,
        [{"k": 0.4}, {"k": 0.6}],
        train_size=100,
        test_size=50,
    )
    assert len(out["windows"]) == 3  # (250-100)//50
    assert not out["oos_equity"].index.has_duplicates
    assert out["oos_equity"].index.is_monotonic_increasing


def test_split_windows_no_overlap(synthetic_ohlcv):
    for train, test in split_windows(synthetic_ohlcv, 100, 50):
        assert train.index[-1] < test.index[0]
        assert len(train) == 100 and len(test) == 50


def test_dual_momentum_weights_and_backtest():
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2022-01-03", periods=750)
    prices = pd.DataFrame(
        {
            "A": 100 * np.exp(np.cumsum(rng.normal(0.001, 0.01, 750))),   # 강한 상승
            "B": 100 * np.exp(np.cumsum(rng.normal(-0.001, 0.01, 750))),  # 하락
            "C": 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, 750))),
        },
        index=dates,
    )
    weights = momentum_weights(prices, lookback_months=6, top_n=1)
    # 상승 종목 A가 가장 자주 선택되어야 함
    picks = (weights > 0).sum()
    assert picks["A"] > picks["B"]
    # 비중 합은 0(전량 현금) 또는 1/top_n 배수
    assert ((weights.sum(axis=1) >= 0) & (weights.sum(axis=1) <= 1.0001)).all()

    returns = backtest_monthly(prices, weights)
    assert len(returns) > 0
