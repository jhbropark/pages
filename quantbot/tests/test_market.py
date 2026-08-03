from quantbot.market import (
    is_limit_down,
    is_limit_up,
    lower_limit,
    round_to_tick,
    tick_size,
    upper_limit,
)


def test_tick_table_2023_revision():
    assert tick_size(1_999) == 1
    assert tick_size(2_000) == 5
    assert tick_size(4_999) == 5
    assert tick_size(5_000) == 10
    assert tick_size(19_999) == 10
    assert tick_size(20_000) == 50
    assert tick_size(49_999) == 50
    assert tick_size(50_000) == 100
    assert tick_size(199_999) == 100
    assert tick_size(200_000) == 500
    assert tick_size(499_999) == 500
    assert tick_size(500_000) == 1_000
    assert tick_size(1_000_000) == 1_000


def test_round_to_tick():
    assert round_to_tick(10_123, "down") == 10_120
    assert round_to_tick(10_123, "up") == 10_130
    assert round_to_tick(10_125, "nearest") in (10_120, 10_130)
    assert round_to_tick(10_120, "up") == 10_120  # 이미 정렬된 가격은 그대로


def test_price_limits():
    # 전일 종가 10,000원 → 상한 13,000 / 하한 7,000
    assert upper_limit(10_000) == 13_000
    assert lower_limit(10_000) == 7_000
    assert is_limit_up(13_000, 10_000)
    assert not is_limit_up(12_990, 10_000)
    assert is_limit_down(7_000, 10_000)
    assert not is_limit_down(7_010, 10_000)
