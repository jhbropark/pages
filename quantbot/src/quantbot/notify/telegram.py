"""Telegram 알림 — 체결/에러/일일 손익. 토큰 미설정 시 로그로만 남긴다."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, text: str) -> bool:
        if not self.enabled:
            log.info("[telegram 미설정] %s", text)
            return False
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text},
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            # 알림 실패가 매매를 멈추게 해서는 안 된다
            log.error("telegram 전송 실패: %s", e)
            return False

    def fill(self, side: str, ticker: str, qty: int, price: float) -> None:
        self.send(f"✅ 체결 {side} {ticker} {qty}주 @ {price:,.0f}원")

    def error(self, message: str) -> None:
        self.send(f"🚨 오류: {message}")

    def daily_report(self, equity: float, pnl: float, pnl_pct: float) -> None:
        emoji = "📈" if pnl >= 0 else "📉"
        self.send(
            f"{emoji} 일일 결산 — 평가액 {equity:,.0f}원, "
            f"손익 {pnl:+,.0f}원 ({pnl_pct:+.2%})"
        )
