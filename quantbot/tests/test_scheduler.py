from datetime import datetime

from quantbot.runtime import scheduler
from quantbot.runtime.scheduler import (
    KST,
    is_open_time,
    is_trading_day,
    seconds_until_open,
    session_phase,
)


def dt(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=KST)


def test_is_trading_day_weekends():
    assert is_trading_day(dt(2026, 7, 17, 10, 0).date())   # 금
    assert not is_trading_day(dt(2026, 7, 18, 10, 0).date())  # 토
    assert not is_trading_day(dt(2026, 7, 19, 10, 0).date())  # 일


def test_is_open_time_boundaries():
    assert not is_open_time(dt(2026, 7, 17, 8, 59))
    assert is_open_time(dt(2026, 7, 17, 9, 0))     # 개장 정각 포함
    assert is_open_time(dt(2026, 7, 17, 15, 29))
    assert not is_open_time(dt(2026, 7, 17, 15, 30))  # 마감 정각 제외
    assert not is_open_time(dt(2026, 7, 18, 10, 0))   # 토요일


def test_session_phase():
    assert session_phase(dt(2026, 7, 17, 8, 0)) == "pre"
    assert session_phase(dt(2026, 7, 17, 12, 0)) == "regular"
    assert session_phase(dt(2026, 7, 17, 16, 0)) == "closed"
    assert session_phase(dt(2026, 7, 18, 12, 0)) == "closed"  # 주말


def test_seconds_until_open():
    assert seconds_until_open(dt(2026, 7, 17, 9, 30)) == 0.0  # 장중
    # 개장 1시간 전
    assert seconds_until_open(dt(2026, 7, 17, 8, 0)) == 3600.0
    # 금요일 마감 후 → 다음 월요일(7/20) 개장
    fri_after = dt(2026, 7, 17, 16, 0)
    secs = seconds_until_open(fri_after)
    assert secs == (dt(2026, 7, 20, 9, 0) - fri_after).total_seconds()


def test_holidays_override(monkeypatch):
    monkeypatch.setattr(scheduler, "HOLIDAYS", frozenset({"2026-07-17"}))
    assert not is_trading_day(dt(2026, 7, 17, 10, 0).date())
    assert not is_open_time(dt(2026, 7, 17, 10, 0))
