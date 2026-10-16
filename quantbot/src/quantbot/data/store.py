"""OHLCV storage — parquet per (ticker, interval) under data/.

스키마: DatetimeIndex(date), columns = open/high/low/close/volume (float64/int64).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import DATA_DIR

COLUMNS = ["open", "high", "low", "close", "volume"]


def _path(ticker: str, interval: str, base: Path | None = None) -> Path:
    base = base or DATA_DIR
    return base / interval / f"{ticker}.parquet"


def save_ohlcv(
    df: pd.DataFrame, ticker: str, interval: str = "1d", base: Path | None = None
) -> Path:
    """기존 파일과 병합 저장(중복 날짜는 새 데이터 우선)."""
    path = _path(ticker, interval, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df[COLUMNS].sort_index()
    if path.exists():
        old = pd.read_parquet(path)
        df = pd.concat([old, df])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(path)
    return path


def load_ohlcv(
    ticker: str,
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
    base: Path | None = None,
) -> pd.DataFrame:
    path = _path(ticker, interval, base)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} 없음 — 먼저 `quantbot fetch {ticker}` 로 수집하세요."
        )
    df = pd.read_parquet(path)
    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]
    return df
