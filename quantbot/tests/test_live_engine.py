import pandas as pd

from quantbot.config import RiskConfig
from quantbot.execution.broker import DryRunBroker, Position
from quantbot.notify.telegram import TelegramNotifier
from quantbot.risk.manager import RiskManager
from quantbot.runtime.engine import LiveEngine
from quantbot.strategy.base import Order, Strategy
from quantbot.strategy.volatility_breakout import VolatilityBreakout


def make_history(rows):
    df = pd.DataFrame(rows, index=pd.bdate_range("2026-01-02", periods=len(rows)))
    df.index.name = "date"
    return df


def make_engine(broker, strategies, risk=None):
    risk = risk or RiskManager(RiskConfig())
    notifier = TelegramNotifier()  # 미설정 → 로그만
    return LiveEngine(broker, strategies, risk, notifier, lambda t: strategies[t]._hist)


class _HistStrategy(Strategy):
    """테스트용: 주입한 history/orders를 그대로 사용."""

    warmup = 1

    def __init__(self, hist, orders_fn):
        self._hist = hist
        self._orders_fn = orders_fn

    def on_bar(self, history, today_open, holding):
        return self._orders_fn(today_open, holding)


def test_open_sell_then_stop_buy_lifecycle():
    hist = make_history(
        [{"open": 10_000, "high": 10_200, "low": 9_800, "close": 10_000, "volume": 1000}]
    )
    # 보유 없음 → 시가엔 주문 없음, stop 매수만 (목표가 10,300)
    strat = _HistStrategy(
        hist,
        lambda o, holding: [Order(side="buy", kind="stop", stop_price=10_300)],
    )
    broker = DryRunBroker(cash=10_000_000, prices={"A": 10_000})
    eng = make_engine(broker, {"A": strat})

    eng.open_session()
    assert broker.fills == []  # 아직 미트리거
    broker.set_price("A", 10_100)
    eng.poll()
    assert broker.fills == []  # 목표가 미달
    broker.set_price("A", 10_400)
    eng.poll()
    assert len(broker.fills) == 1 and broker.fills[0][0] == "buy"  # 돌파 → 매수
    eng.close_session()


def test_open_sell_liquidates_holding():
    hist = make_history(
        [{"open": 10_000, "high": 10_200, "low": 9_800, "close": 10_000, "volume": 1000}]
    )
    strat = _HistStrategy(hist, lambda o, holding: [Order(side="sell", kind="open")])
    broker = DryRunBroker(cash=0, prices={"A": 10_000})
    broker._positions["A"] = Position("A", 100, 9_000)  # 기존 보유
    eng = make_engine(broker, {"A": strat})

    eng.open_session()
    assert broker.fills == [("sell", "A", 100, 10_000)]
    assert "A" not in broker.snapshot().positions


def test_risk_caps_position_weight():
    hist = make_history(
        [{"open": 10_000, "high": 10_200, "low": 9_800, "close": 10_000, "volume": 1000}]
    )
    # weight=1.0 로 전액 매수 시도하지만 종목당 비중 10% 한도가 걸린다
    strat = _HistStrategy(
        hist, lambda o, holding: [Order(side="buy", kind="open", weight=1.0)]
    )
    broker = DryRunBroker(cash=10_000_000, prices={"A": 10_000})
    eng = make_engine(broker, {"A": strat}, RiskManager(RiskConfig(max_position_weight=0.10)))

    eng.open_session()
    assert len(broker.fills) == 1
    _, _, qty, price = broker.fills[0]
    # 1000만 × 10% / 10,000원 = 100주 (한도)
    assert qty == 100


def test_daily_loss_limit_kills_intraday_buys():
    hist = make_history(
        [{"open": 10_000, "high": 10_200, "low": 9_800, "close": 10_000, "volume": 1000}]
    )
    strat = _HistStrategy(
        hist, lambda o, holding: [Order(side="buy", kind="stop", stop_price=10_050)]
    )
    risk = RiskManager(RiskConfig(daily_loss_limit=0.03))
    broker = DryRunBroker(cash=10_000_000, prices={"A": 10_000})
    eng = make_engine(broker, {"A": strat}, risk)

    eng.open_session()  # day_start_equity = 1000만
    # 계좌가 -4% 급락한 상황을 모의: 평가금액을 떨어뜨림
    broker._cash = 9_600_000
    broker.set_price("A", 10_100)  # stop 트리거 조건은 충족
    eng.poll()
    assert risk.killed
    assert broker.fills == []  # 손실 한도로 신규 매수 차단


def test_volatility_breakout_end_to_end():
    # 전일 range 1,000, 오늘 시가 10,000, k=0.5 → 목표가 10,500
    hist = make_history(
        [
            {"open": 9_500, "high": 10_000, "low": 9_000, "close": 9_800, "volume": 1000},
            {"open": 9_900, "high": 10_400, "low": 9_700, "close": 10_000, "volume": 1000},
        ]
    )
    strat = VolatilityBreakout(k=0.5)
    strat._hist = hist  # make_engine 의 history_provider 규약
    broker = DryRunBroker(cash=10_000_000, prices={"A": 10_000}, opens={"A": 10_000})
    eng = make_engine(broker, {"A": strat})

    eng.open_session()
    assert broker.fills == []
    broker.set_price("A", 10_600)  # 목표가 10,500 돌파
    eng.poll()
    assert len(broker.fills) == 1 and broker.fills[0][0] == "buy"
    eng.close_session()
