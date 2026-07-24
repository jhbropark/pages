"""KIS API 호출 제한 대응 — 초당 N건 토큰 버킷.

실전 계좌는 초당 20건, 모의투자는 초당 2건. 넘으면 EGW00201 오류가 난다.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_calls: int, per_seconds: float = 1.0):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """호출 허용될 때까지 블록."""
        while True:
            with self._lock:
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= self.per_seconds:
                    self._calls.popleft()
                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return
                wait = self.per_seconds - (now - self._calls[0])
            time.sleep(max(wait, 0.01))
