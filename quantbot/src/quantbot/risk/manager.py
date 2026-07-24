"""실거래용 리스크 게이트 — 모든 주문은 여기를 통과해야 한다.

책임:
  - 종목당 최대 비중 / 최대 보유 종목 수 제한
  - 일일 손실 한도 도달 시 신규 매수 차단 (거래 정지)
  - kill switch: API 연속 오류·급락 감지 시 발동, 신규 주문 전면 차단
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..config import RiskConfig

log = logging.getLogger(__name__)


@dataclass
class RiskManager:
    config: RiskConfig
    day_start_equity: float = 0.0
    _killed: bool = field(default=False, init=False)
    _kill_reason: str = field(default="", init=False)
    _api_error_streak: int = field(default=0, init=False)

    API_ERROR_KILL_THRESHOLD = 5

    # --- 상태 갱신 -------------------------------------------------------
    def start_day(self, equity: float) -> None:
        self.day_start_equity = equity

    def record_api_error(self) -> None:
        self._api_error_streak += 1
        if self._api_error_streak >= self.API_ERROR_KILL_THRESHOLD:
            self.kill(f"API 연속 오류 {self._api_error_streak}회")

    def record_api_success(self) -> None:
        self._api_error_streak = 0

    def kill(self, reason: str) -> None:
        if not self._killed:
            log.critical("KILL SWITCH: %s", reason)
        self._killed = True
        self._kill_reason = reason

    @property
    def killed(self) -> bool:
        return self._killed

    @property
    def kill_reason(self) -> str:
        return self._kill_reason

    # --- 주문 게이트 -----------------------------------------------------
    def daily_loss_exceeded(self, current_equity: float) -> bool:
        if self.day_start_equity <= 0:
            return False
        loss = 1 - current_equity / self.day_start_equity
        return loss >= self.config.daily_loss_limit

    def can_buy(
        self,
        current_equity: float,
        order_value: float,
        position_value: float,
        num_positions: int,
    ) -> tuple[bool, str]:
        """(허용 여부, 거부 사유). position_value = 해당 종목 기존 보유 평가액."""
        if self._killed:
            return False, f"kill switch 발동: {self._kill_reason}"
        if self.daily_loss_exceeded(current_equity):
            return False, "일일 손실 한도 도달 — 오늘 신규 매수 정지"
        if num_positions >= self.config.max_positions and position_value == 0:
            return False, f"최대 보유 종목 수({self.config.max_positions}) 초과"
        if current_equity > 0:
            weight = (position_value + order_value) / current_equity
            if weight > self.config.max_position_weight:
                return False, (
                    f"종목 비중 {weight:.1%} > 한도 "
                    f"{self.config.max_position_weight:.0%}"
                )
        return True, ""

    def can_sell(self) -> tuple[bool, str]:
        # 청산은 kill switch 상태에서도 허용 (리스크 축소 방향)
        return True, ""
