import pytest

from quantbot.execution.broker import (
    AccountSnapshot,
    Broker,
    DryRunBroker,
    KISBroker,
    Position,
)


def test_dryrun_buy_sell_roundtrip():
    b = DryRunBroker(cash=1_000_000, prices={"005930": 70_000})
    assert isinstance(b, Broker)  # Protocol 준수

    b.buy("005930", 10)
    snap = b.snapshot()
    assert snap.positions["005930"].qty == 10
    assert snap.cash == pytest.approx(1_000_000 - 70_000 * 10)
    assert snap.held("005930")

    b.sell("005930", 10)
    snap = b.snapshot()
    assert "005930" not in snap.positions
    assert snap.cash == pytest.approx(1_000_000)
    assert [f[0] for f in b.fills] == ["buy", "sell"]


def test_dryrun_rejects_overspend_and_oversell():
    b = DryRunBroker(cash=100_000, prices={"005930": 70_000})
    with pytest.raises(RuntimeError):
        b.buy("005930", 10)  # 70만원 > 현금 10만원
    with pytest.raises(RuntimeError):
        b.sell("005930", 1)  # 미보유


def test_dryrun_equity_tracks_price():
    b = DryRunBroker(cash=1_000_000, prices={"005930": 70_000})
    b.buy("005930", 10)
    b.set_price("005930", 80_000)
    snap = b.snapshot()
    # 현금 30만 + 평가 80만 = 110만
    assert snap.total_equity == pytest.approx(300_000 + 800_000)


class _FakeKISClient:
    """KISBroker 파싱 검증용 가짜 KISClient."""

    def current_price(self, ticker):
        return {"stck_prpr": "70000", "stck_oprc": "69500"}

    def balance(self):
        return {
            "output1": [
                {"pdno": "005930", "hldg_qty": "10", "pchs_avg_pric": "68000"},
                {"pdno": "000660", "hldg_qty": "0", "pchs_avg_pric": "0"},  # 잔량0 제외
            ],
            "output2": [{"tot_evlu_amt": "1500000", "dnca_tot_amt": "800000"}],
        }

    def order_cash(self, ticker, qty, side, price=0):
        self.last = (ticker, qty, side, price)
        return {}


def test_kisbroker_parses_responses():
    broker = KISBroker(_FakeKISClient())
    assert broker.current_price("005930") == 70_000.0
    assert broker.today_open("005930") == 69_500.0

    snap = broker.snapshot()
    assert isinstance(snap, AccountSnapshot)
    assert snap.total_equity == 1_500_000.0
    assert snap.cash == 800_000.0
    assert set(snap.positions) == {"005930"}  # 잔량 0 종목은 빠짐
    assert snap.positions["005930"] == Position("005930", 10, 68_000.0)


def test_kisbroker_sends_market_orders():
    client = _FakeKISClient()
    broker = KISBroker(client)
    broker.buy("005930", 5)
    assert client.last == ("005930", 5, "buy", 0)
    broker.sell("005930", 5)
    assert client.last == ("005930", 5, "sell", 0)
