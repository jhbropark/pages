"""Central configuration. Secrets come from environment / .env, never from code."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class KISConfig:
    app_key: str = ""
    app_secret: str = ""
    account_no: str = ""
    env: str = "paper"  # "paper" (모의투자) | "real"

    @property
    def base_url(self) -> str:
        if self.env == "real":
            return "https://openapi.koreainvestment.com:9443"
        return "https://openapivts.koreainvestment.com:29443"

    @classmethod
    def from_env(cls) -> "KISConfig":
        return cls(
            app_key=os.getenv("KIS_APP_KEY", ""),
            app_secret=os.getenv("KIS_APP_SECRET", ""),
            account_no=os.getenv("KIS_ACCOUNT_NO", ""),
            env=os.getenv("KIS_ENV", "paper"),
        )


@dataclass(frozen=True)
class CostConfig:
    """KRX trading costs. Rates are fractions (0.00015 == 0.015%)."""

    commission_rate: float = 0.00015     # 위탁수수료, 매수/매도 각각
    # 증권거래세+농특세: 2025년부터 코스피/코스닥 합산 0.15%.
    # 2024년 이전 데이터로 백테스트할 때는 0.0018로 올려서 보수적으로.
    sell_tax_rate: float = 0.0015
    slippage_rate: float = 0.0005        # 시장가 체결 가정 슬리피지 (편도)


@dataclass(frozen=True)
class RiskConfig:
    max_position_weight: float = 0.10    # 종목당 최대 비중
    daily_loss_limit: float = 0.03       # 일일 손실 한도 (계좌 대비) — 도달 시 거래 정지
    max_positions: int = 10
    kelly_fraction: float = 0.25         # Kelly의 1/4


@dataclass(frozen=True)
class Settings:
    kis: KISConfig = field(default_factory=KISConfig.from_env)
    costs: CostConfig = field(default_factory=CostConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    telegram_bot_token: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_chat_id: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", "")
    )


def load_settings() -> Settings:
    return Settings()
