"""KIS OAuth 토큰 발급/캐싱.

접근토큰은 24시간 유효하고 발급 자체에 1분당 1회 제한이 있으므로
반드시 파일에 캐싱해 재사용한다.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from ..config import PROJECT_ROOT, KISConfig

TOKEN_CACHE = PROJECT_ROOT / ".kis_token.json"


class KISAuth:
    def __init__(self, config: KISConfig, cache_path: Path | None = None):
        self.config = config
        self.cache_path = cache_path or TOKEN_CACHE
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._load_cache()

    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            return
        try:
            cached = json.loads(self.cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        if cached.get("env") == self.config.env and cached.get("app_key") == (
            self.config.app_key
        ):
            self._token = cached.get("token")
            self._expires_at = cached.get("expires_at", 0.0)

    def _save_cache(self) -> None:
        self.cache_path.write_text(
            json.dumps(
                {
                    "env": self.config.env,
                    "app_key": self.config.app_key,
                    "token": self._token,
                    "expires_at": self._expires_at,
                }
            )
        )
        self.cache_path.chmod(0o600)

    def token(self) -> str:
        # 만료 10분 전부터 갱신
        if self._token and time.time() < self._expires_at - 600:
            return self._token
        resp = requests.post(
            f"{self.config.base_url}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": self.config.app_key,
                "appsecret": self.config.app_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = time.time() + int(body.get("expires_in", 86400))
        self._save_cache()
        return self._token
