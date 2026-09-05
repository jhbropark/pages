"""KRX 장 시간 인식 스케줄러.

순수 판정 함수(is_trading_day / is_open_time / session_phase / seconds_until_open)는
now를 인자로 받아 테스트 가능하게 두고, 실제 sleep 루프(run)는 그 위의 얇은 껍데기다.

주의: 공휴일 달력은 포함하지 않는다(주말만 제외). 실전 운영 시 KRX 휴장일을
HOLIDAYS에 채우거나 별도 캘린더를 주입할 것.
"""

from __future__ import annotations

import logging
import time as _time
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(15, 30)

#: 추가 휴장일(YYYY-MM-DD). 운영 환경에서 채운다.
HOLIDAYS: frozenset[str] = frozenset()


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS


def is_open_time(now: datetime) -> bool:
    return is_trading_day(now.date()) and MARKET_OPEN <= now.time() < MARKET_CLOSE


def session_phase(now: datetime) -> str:
    """"pre"(개장 전) | "regular"(장중) | "closed"(장 마감/휴장)."""
    if not is_trading_day(now.date()):
        return "closed"
    t = now.time()
    if t < MARKET_OPEN:
        return "pre"
    if t < MARKET_CLOSE:
        return "regular"
    return "closed"


def seconds_until_open(now: datetime) -> float:
    """다음 개장까지 남은 초. 장중이면 0."""
    if is_open_time(now):
        return 0.0
    d = now.date()
    # 오늘 개장 전이면 오늘, 아니면 다음 거래일
    if not (is_trading_day(d) and now.time() < MARKET_OPEN):
        d = _next_trading_day(d)
    target = datetime.combine(d, MARKET_OPEN, tzinfo=now.tzinfo or KST)
    return max(0.0, (target - now).total_seconds())


def _next_trading_day(d: date) -> date:
    nxt = d.fromordinal(d.toordinal() + 1)
    while not is_trading_day(nxt):
        nxt = nxt.fromordinal(nxt.toordinal() + 1)
    return nxt


def run(engine, poll_interval: float = 30.0, *, max_days: int | None = None) -> None:
    """장 시간에 맞춰 engine을 구동하는 상시 루프.

    max_days: 지정 시 그만큼의 거래일만 돌고 종료(테스트/제한 운영용).
    """
    days = 0
    while max_days is None or days < max_days:
        now = datetime.now(KST)
        wait = seconds_until_open(now)
        if wait > 0:
            log.info("개장까지 %.0f분 대기", wait / 60)
            _time.sleep(wait)

        log.info("=== 장 시작 세션 ===")
        engine.open_session()
        while is_open_time(datetime.now(KST)):
            engine.poll()
            _time.sleep(poll_interval)
        log.info("=== 장 마감 세션 ===")
        engine.close_session()
        days += 1
        # 다음 거래일 개장 전까지 대기(중복 실행 방지)
        _time.sleep(max(0.0, seconds_until_open(datetime.now(KST))))
