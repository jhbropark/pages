"""성과지표: CAGR, MDD, Sharpe, 승률, Profit Factor."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = len(equity) / TRADING_DAYS
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def max_drawdown(equity: pd.Series) -> float:
    """최대 낙폭 (음수, 예: -0.23)."""
    if equity.empty:
        return 0.0
    dd = equity / equity.cummax() - 1
    return float(dd.min())


def sharpe(equity: pd.Series, risk_free: float = 0.0) -> float:
    returns = equity.pct_change().dropna()
    if returns.std() == 0 or returns.empty:
        return 0.0
    excess = returns - risk_free / TRADING_DAYS
    return float(excess.mean() / returns.std() * np.sqrt(TRADING_DAYS))


def win_rate(pnls: pd.Series) -> float:
    closed = pnls.dropna()
    if closed.empty:
        return 0.0
    return float((closed > 0).mean())


def profit_factor(pnls: pd.Series) -> float:
    closed = pnls.dropna()
    gains = closed[closed > 0].sum()
    losses = -closed[closed < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def summarize(equity: pd.Series, trades: pd.DataFrame | None = None) -> dict:
    out = {
        "start": str(equity.index[0].date()) if len(equity) else None,
        "end": str(equity.index[-1].date()) if len(equity) else None,
        "final_equity": float(equity.iloc[-1]) if len(equity) else 0.0,
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1)
        if len(equity)
        else 0.0,
        "cagr": cagr(equity),
        "mdd": max_drawdown(equity),
        "sharpe": sharpe(equity),
    }
    if trades is not None and not trades.empty:
        pnls = trades["pnl"]
        out |= {
            "num_trades": int(len(trades)),
            "win_rate": win_rate(pnls),
            "profit_factor": profit_factor(pnls),
        }
    return out
