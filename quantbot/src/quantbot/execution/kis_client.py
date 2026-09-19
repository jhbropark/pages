"""한국투자증권 KIS Developers REST 클라이언트 (국내주식 현금주문).

tr_id가 실전/모의로 다르므로 config.env에 따라 자동 선택한다.
문서: https://apiportal.koreainvestment.com
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from ..config import KISConfig
from .kis_auth import KISAuth
from .rate_limiter import RateLimiter

log = logging.getLogger(__name__)

# (실전, 모의)
_TR_IDS = {
    "buy": ("TTTC0802U", "VTTC0802U"),
    "sell": ("TTTC0801U", "VTTC0801U"),
    "balance": ("TTTC8434R", "VTTC8434R"),
}


class KISError(RuntimeError):
    pass


class KISClient:
    def __init__(self, config: KISConfig):
        if not config.app_key or not config.app_secret:
            raise KISError("KIS_APP_KEY / KIS_APP_SECRET 환경변수를 설정하세요")
        self.config = config
        self.auth = KISAuth(config)
        # 모의투자는 초당 2건, 실전은 초당 20건 제한
        self.limiter = RateLimiter(20 if config.env == "real" else 2)
        cano, _, prdt = config.account_no.partition("-")
        self._cano = cano
        self._prdt = prdt or "01"

    def _tr_id(self, kind: str) -> str:
        real, paper = _TR_IDS[kind]
        return real if self.config.env == "real" else paper

    def _headers(self, tr_id: str) -> dict[str, str]:
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.auth.token()}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    def _request(
        self,
        method: str,
        path: str,
        tr_id: str,
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict[str, Any]:
        self.limiter.acquire()
        resp = requests.request(
            method,
            f"{self.config.base_url}{path}",
            headers=self._headers(tr_id),
            params=params,
            json=body,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("rt_cd") not in (None, "0"):
            raise KISError(f"{data.get('msg_cd')}: {data.get('msg1')}")
        return data

    # --- 시세 -------------------------------------------------------------
    def current_price(self, ticker: str) -> dict[str, Any]:
        """현재가/전일대비 등. output.stck_prpr = 현재가."""
        data = self._request(
            "GET",
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id="FHKST01010100",
            params={"fid_cond_mrkt_div_code": "J", "fid_input_iscd": ticker},
        )
        return data["output"]

    # --- 계좌 -------------------------------------------------------------
    def balance(self) -> dict[str, Any]:
        """잔고 조회. output1 = 보유 종목, output2 = 계좌 요약."""
        return self._request(
            "GET",
            "/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id=self._tr_id("balance"),
            params={
                "CANO": self._cano,
                "ACNT_PRDT_CD": self._prdt,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "00",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
        )

    # --- 주문 -------------------------------------------------------------
    def order_cash(
        self, ticker: str, qty: int, side: str, price: int = 0
    ) -> dict[str, Any]:
        """현금 주문. price=0이면 시장가, 아니면 지정가.

        side: "buy" | "sell"
        """
        if side not in ("buy", "sell"):
            raise ValueError("side는 buy/sell")
        if qty <= 0:
            raise ValueError("qty는 양수")
        body = {
            "CANO": self._cano,
            "ACNT_PRDT_CD": self._prdt,
            "PDNO": ticker,
            "ORD_DVSN": "01" if price == 0 else "00",  # 01 시장가, 00 지정가
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price),
        }
        data = self._request(
            "POST",
            "/uapi/domestic-stock/v1/trading/order-cash",
            tr_id=self._tr_id(side),
            body=body,
        )
        log.info("주문 접수 %s %s x%d @%s → %s", side, ticker, qty, price, data.get("msg1"))
        return data["output"]
