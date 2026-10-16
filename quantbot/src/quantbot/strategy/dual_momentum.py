"""듀얼 모멘텀 (절대 + 상대) — 월 단위 리밸런싱.

다종목 포트폴리오 전략이라 단일 종목 이벤트 엔진과 별도로,
월말 종가 패널(가격 DataFrame: index=date, columns=ticker)에 대해
목표 비중을 계산하는 함수형 구현. 실거래에서는 월 1회 실행하면 된다.
"""

from __future__ import annotations

import pandas as pd


def momentum_weights(
    prices: pd.DataFrame,
    lookback_months: int = 12,
    top_n: int = 2,
    absolute_threshold: float = 0.0,
) -> pd.DataFrame:
    """월말 리밸런싱 목표 비중.

    상대 모멘텀: lookback 수익률 상위 top_n 선택.
    절대 모멘텀: lookback 수익률이 threshold 이하인 종목은 현금(비중 0)으로.
    반환: index=리밸런싱일(월말), columns=ticker, 값=목표 비중.
    """
    monthly = prices.resample("ME").last()
    returns = monthly.pct_change(lookback_months)
    weights = pd.DataFrame(0.0, index=monthly.index, columns=monthly.columns)

    for date, row in returns.dropna(how="all").iterrows():
        ranked = row.dropna().sort_values(ascending=False).head(top_n)
        selected = ranked[ranked > absolute_threshold]
        if len(selected):
            weights.loc[date, selected.index] = 1.0 / top_n  # 미달분은 현금 보유
    return weights


def backtest_monthly(
    prices: pd.DataFrame,
    weights: pd.DataFrame,
    cost_per_rebalance: float = 0.003,
) -> pd.Series:
    """월 단위 근사 백테스트 — 다음 달 수익률에 이번 달 비중 적용.

    cost_per_rebalance: 회전율 1.0당 왕복 비용 근사 (수수료+세금+슬리피지).
    반환: 월별 포트폴리오 수익률 Series.
    """
    monthly_returns = prices.resample("ME").last().pct_change()
    port = (weights.shift(1) * monthly_returns).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).shift(1).fillna(0.0)
    return (port - turnover * cost_per_rebalance).dropna()
