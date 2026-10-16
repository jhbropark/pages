import pytest

from quantbot.config import RiskConfig
from quantbot.risk.manager import RiskManager
from quantbot.risk.sizing import fixed_fraction, kelly_fraction


def make_manager() -> RiskManager:
    rm = RiskManager(RiskConfig(max_position_weight=0.10, daily_loss_limit=0.03, max_positions=2))
    rm.start_day(10_000_000)
    return rm


def test_position_weight_limit():
    rm = make_manager()
    ok, _ = rm.can_buy(10_000_000, order_value=900_000, position_value=0, num_positions=0)
    assert ok
    ok, reason = rm.can_buy(10_000_000, order_value=1_500_000, position_value=0, num_positions=0)
    assert not ok and "비중" in reason


def test_daily_loss_limit_blocks_buys():
    rm = make_manager()
    ok, _ = rm.can_buy(9_800_000, 100_000, 0, 0)  # -2%: 허용
    assert ok
    ok, reason = rm.can_buy(9_600_000, 100_000, 0, 0)  # -4%: 차단
    assert not ok and "손실 한도" in reason


def test_max_positions():
    rm = make_manager()
    ok, reason = rm.can_buy(10_000_000, 100_000, position_value=0, num_positions=2)
    assert not ok and "종목 수" in reason
    # 기존 보유 종목 추가 매수는 종목 수 제한과 무관
    ok, _ = rm.can_buy(10_000_000, 100_000, position_value=500_000, num_positions=2)
    assert ok


def test_kill_switch_on_api_errors():
    rm = make_manager()
    for _ in range(RiskManager.API_ERROR_KILL_THRESHOLD):
        rm.record_api_error()
    assert rm.killed
    ok, reason = rm.can_buy(10_000_000, 100_000, 0, 0)
    assert not ok and "kill" in reason.lower()
    # 청산은 여전히 허용
    ok, _ = rm.can_sell()
    assert ok


def test_api_success_resets_streak():
    rm = make_manager()
    for _ in range(RiskManager.API_ERROR_KILL_THRESHOLD - 1):
        rm.record_api_error()
    rm.record_api_success()
    rm.record_api_error()
    assert not rm.killed


def test_fixed_fraction():
    assert fixed_fraction(10_000_000, 50_000, 0.10) == 20
    assert fixed_fraction(10_000_000, 0, 0.10) == 0


def test_kelly_quarter():
    # 승률 60%, 손익비 1:1 → full Kelly 0.2 → 1/4 Kelly 0.05
    assert kelly_fraction(0.6, 0.05, 0.05, scale=0.25) == pytest.approx(0.05)
    # 음수 Kelly는 0
    assert kelly_fraction(0.3, 0.05, 0.05, scale=0.25) == 0.0
