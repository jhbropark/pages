import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """재현 가능한 합성 일봉 250개 (시드 고정, 1만원대 종목)."""
    rng = np.random.default_rng(42)
    n = 250
    dates = pd.bdate_range("2025-01-02", periods=n)
    close = 10_000 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, n)))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.02, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.02, n))
    volume = rng.integers(100_000, 1_000_000, n)
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
    df.index.name = "date"
    return df.round(0)
