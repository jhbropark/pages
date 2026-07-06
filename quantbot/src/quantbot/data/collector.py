"""과거 데이터 백필.

소스 두 가지:
  - fdr (기본): FinanceDataReader, 네이버 금융 기반 — 로그인 불필요
  - pykrx: KRX 공식 데이터. 최신 pykrx는 KRX_ID/KRX_PW 환경변수(데이터포털
    로그인)가 필요하다. 미설정 시 빈 DataFrame이 온다.
"""

from __future__ import annotations

import pandas as pd

_PYKRX_RENAME = {
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "종가": "close",
    "거래량": "volume",
}

_FDR_RENAME = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}

_DTYPES = {"open": float, "high": float, "low": float, "close": float, "volume": int}


class EmptyDataError(RuntimeError):
    pass


def fetch_daily(ticker: str, start: str, end: str, source: str = "fdr") -> pd.DataFrame:
    """일봉 수집. ticker는 6자리 종목코드(예: '005930'), 날짜는 YYYYMMDD."""
    if source == "fdr":
        return fetch_daily_fdr(ticker, start, end)
    if source == "pykrx":
        return fetch_daily_pykrx(ticker, start, end)
    raise ValueError(f"알 수 없는 소스: {source}")


def fetch_daily_fdr(ticker: str, start: str, end: str) -> pd.DataFrame:
    import FinanceDataReader as fdr  # lazy import

    df = fdr.DataReader(ticker, pd.Timestamp(start), pd.Timestamp(end))
    if df.empty:
        raise EmptyDataError(f"{ticker}: FinanceDataReader가 빈 데이터를 반환")
    df = df.rename(columns=_FDR_RENAME)[list(_FDR_RENAME.values())]
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df.astype(_DTYPES)


def fetch_daily_pykrx(ticker: str, start: str, end: str) -> pd.DataFrame:
    from pykrx import stock  # lazy import

    df = stock.get_market_ohlcv(start, end, ticker)
    if df.empty:
        raise EmptyDataError(
            f"{ticker}: pykrx가 빈 데이터를 반환 — 최신 pykrx는 KRX 데이터포털 "
            "로그인이 필요합니다 (KRX_ID/KRX_PW 환경변수). "
            "또는 --source fdr 를 사용하세요."
        )
    df = df.rename(columns=_PYKRX_RENAME)[list(_PYKRX_RENAME.values())]
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    # 거래정지일은 거래량 0으로 들어옴 — 백테스트에서 체결 불가 처리에 쓰이므로 유지
    return df.astype(_DTYPES)


def list_tickers(market: str = "KOSPI", date: str | None = None) -> list[str]:
    from pykrx import stock

    return stock.get_market_ticker_list(date, market=market)
