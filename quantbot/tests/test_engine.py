import pandas as pd
import pytest

from quantbot.backtest.engine import run_backtest
from quantbot.config import CostConfig
from quantbot.strategy.base import Order, Strategy


def make_df(rows: list[dict], start: str = "2025-01-02") -> pd.DataFrame:
    df = pd.DataFrame(rows, index=pd.bdate_range(start, periods=len(rows)))
    df.index.name = "date"
    return df


class BuyOpenSellNextOpen(Strategy):
    """둘째 날 시가 매수, 셋째 날 시가 매도 — 체결 가격 검증용."""

    warmup = 1

    def on_bar(self, history, today_open, holding):
        if holding:
            return [Order(side="sell", kind="open")]
        if len(history) == 1:
            return [Order(side="buy", kind="open")]
        return []


ZERO_COSTS = CostConfig(commission_rate=0, sell_tax_rate=0, slippage_rate=0)


def test_fill_prices_and_pnl_zero_cost():
    df = make_df(
        [
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
            {"open": 10_000, "high": 10_500, "low": 9_900, "close": 10_400, "volume": 1000},
            {"open": 11_000, "high": 11_200, "low": 10_800, "close": 11_100, "volume": 1000},
        ]
    )
    result = run_backtest(df, BuyOpenSellNextOpen(), 10_000_000, ZERO_COSTS)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_price == 10_000
    assert trade.exit_price == 11_000
    assert trade.qty == 1000
    assert trade.pnl == pytest.approx(1_000 * 1000)
    assert result.equity.iloc[-1] == pytest.approx(11_000_000)


def test_costs_reduce_pnl():
    df = make_df(
        [
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
        ]
    )
    costs = CostConfig(commission_rate=0.00015, sell_tax_rate=0.0015, slippage_rate=0.0005)
    result = run_backtest(df, BuyOpenSellNextOpen(), 10_000_000, costs)
    # 가격 변동 없이 사고팔면 비용만큼 손실
    assert result.trades[0].pnl < 0
    assert result.equity.iloc[-1] < 10_000_000


def test_halted_day_no_fill():
    df = make_df(
        [
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 0},
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
        ]
    )
    result = run_backtest(df, BuyOpenSellNextOpen(), 10_000_000, ZERO_COSTS)
    # 둘째 날 거래정지 → 매수는 셋째 날 (history 길이 2에서는 주문 안 냄) → 체결 없음
    assert len(result.trades) == 0


def test_limit_up_locked_blocks_buy():
    # 둘째 날 상한가 잠김 (전일 종가 10,000 → 13,000에 고정)
    df = make_df(
        [
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
            {"open": 13_000, "high": 13_000, "low": 13_000, "close": 13_000, "volume": 1000},
            {"open": 13_000, "high": 13_100, "low": 12_900, "close": 13_000, "volume": 1000},
        ]
    )
    result = run_backtest(df, BuyOpenSellNextOpen(), 10_000_000, ZERO_COSTS)
    assert len(result.trades) == 0


class StopBuyAt10500(Strategy):
    warmup = 1

    def on_bar(self, history, today_open, holding):
        if not holding:
            return [Order(side="buy", kind="stop", stop_price=10_500)]
        return []


def test_stop_buy_triggers_only_when_high_reached():
    df = make_df(
        [
            {"open": 10_000, "high": 10_100, "low": 9_900, "close": 10_000, "volume": 1000},
            {"open": 10_000, "high": 10_400, "low": 9_900, "close": 10_300, "volume": 1000},  # 미도달
            {"open": 10_200, "high": 10_800, "low": 10_100, "close": 10_700, "volume": 1000},  # 도달
        ]
    )
    result = run_backtest(df, StopBuyAt10500(), 10_000_000, ZERO_COSTS)
    assert len(result.trades) == 1
    assert result.trades[0].entry_date == df.index[2]
    assert result.trades[0].entry_price == 10_500  # max(시가, 목표가)


def test_equity_marked_to_market(synthetic_ohlcv):
    result = run_backtest(synthetic_ohlcv, StopBuyAt10500(), 10_000_000, ZERO_COSTS)
    assert len(result.equity) == len(synthetic_ohlcv) - 1  # warmup 제외
    assert (result.equity > 0).all()
