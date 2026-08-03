"""KIS 실시간 체결통보 WebSocket 클라이언트.

KIS는 주문 체결을 WebSocket으로 실시간 통보한다(tr_id: 실전 H0STCNI0 / 모의 H0STCNI9).
접속에는 REST 토큰과 별개인 approval_key가 필요하고, 체결통보 본문은 AES-CBC로
암호화되어 온다. 구독 응답 첫 프레임에 복호화용 key/iv가 담겨 온다.

네트워크·crypto 의존은 지연 import 하므로, 이 모듈 자체는 websockets/pycryptodome
없이도 import 된다(파서·복호화 유틸은 순수 함수라 단위 테스트 가능).
"""

from __future__ import annotations

import json
import logging

import requests

from ..config import KISConfig

log = logging.getLogger(__name__)

_TR_EXEC = ("H0STCNI0", "H0STCNI9")  # (실전, 모의)

# 체결통보 복호문(^ 구분) 필드 레이아웃 (주요 항목만 명명)
_EXEC_FIELDS = [
    "cust_id",        # 0 고객ID
    "account_no",     # 1 계좌번호
    "order_no",       # 2 주문번호
    "orig_order_no",  # 3 원주문번호
    "side",           # 4 매도매수구분 (01 매도 / 02 매수)
    "amend_type",     # 5 정정구분
    "order_kind",     # 6 주문종류
    "order_cond",     # 7 주문조건
    "ticker",         # 8 주식단축종목코드
    "exec_qty",       # 9 체결수량
    "exec_price",     # 10 체결단가
    "exec_time",      # 11 주식체결시간
    "reject_yn",      # 12 거부여부
    "exec_yn",        # 13 체결여부 (1 접수 / 2 체결)
    "accept_yn",      # 14 접수여부
    "branch_no",      # 15 지점번호
    "order_qty",      # 16 주문수량
    "account_name",   # 17 계좌명
    "exec_name",      # 18 체결종목명
    "credit_type",    # 19 신용구분
    "credit_date",    # 20 신용대출일자
]


def get_approval_key(config: KISConfig) -> str:
    """WebSocket 접속용 approval_key 발급."""
    resp = requests.post(
        f"{config.base_url}/oauth2/Approval",
        json={
            "grant_type": "client_credentials",
            "appkey": config.app_key,
            "secretkey": config.app_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["approval_key"]


def parse_execution_notice(decrypted: str) -> dict[str, str]:
    """복호화된 체결통보 본문('^' 구분)을 명명된 dict로 변환."""
    parts = decrypted.split("^")
    notice = {name: parts[i] for i, name in enumerate(_EXEC_FIELDS) if i < len(parts)}
    notice["side_label"] = "sell" if notice.get("side") == "01" else "buy"
    notice["is_filled"] = notice.get("exec_yn") == "2"
    return notice


def aes_cbc_decrypt(key: str, iv: str, cipher_b64: str) -> str:
    """AES-256-CBC 복호화 (PKCS7 언패딩). crypto 의존은 지연 import."""
    import base64

    from Crypto.Cipher import AES  # pycryptodome (live extra)
    from Crypto.Util.Padding import unpad

    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    decrypted = unpad(cipher.decrypt(base64.b64decode(cipher_b64)), AES.block_size)
    return decrypted.decode("utf-8")


class KISWebSocketClient:
    """체결통보 구독 클라이언트. on_execution 콜백으로 체결 dict를 넘긴다."""

    def __init__(self, config: KISConfig):
        self.config = config
        self.approval_key = ""
        self._aes_key = ""
        self._aes_iv = ""

    @property
    def _ws_url(self) -> str:
        # 실전 21000 / 모의 31000
        host = "ops.koreainvestment.com"
        port = 21000 if self.config.env == "real" else 31000
        return f"ws://{host}:{port}"

    @property
    def _tr_id(self) -> str:
        real, paper = _TR_EXEC
        return real if self.config.env == "real" else paper

    def _subscribe_frame(self) -> str:
        return json.dumps(
            {
                "header": {
                    "approval_key": self.approval_key,
                    "custtype": "P",
                    "tr_type": "1",  # 등록
                    "content-type": "utf-8",
                },
                "body": {
                    "input": {"tr_id": self._tr_id, "tr_key": self.config.account_no}
                },
            }
        )

    def _handle_frame(self, raw: str, on_execution) -> None:
        """수신 프레임 1건 처리. 실시간 데이터는 '0|'/'1|'로 시작한다."""
        if raw and raw[0] in "01":
            _flag, _tr, _cnt, body = raw.split("|", 3)
            if self._aes_key:
                body = aes_cbc_decrypt(self._aes_key, self._aes_iv, body)
            notice = parse_execution_notice(body)
            if notice.get("is_filled"):
                on_execution(notice)
            return
        # JSON 제어 프레임: 구독 응답(암호화 key/iv) 또는 PINGPONG
        msg = json.loads(raw)
        if msg.get("body", {}).get("output"):
            out = msg["body"]["output"]
            self._aes_key = out.get("key", self._aes_key)
            self._aes_iv = out.get("iv", self._aes_iv)
            log.info("체결통보 구독 완료 (암호화 키 수신)")

    @staticmethod
    def _is_pingpong(raw: str) -> bool:
        return raw[:1] not in "01" and '"tr_id":"PINGPONG"' in raw.replace(" ", "")

    async def run(self, on_execution) -> None:
        """WebSocket 접속 → 체결통보 구독 → 프레임 수신 루프. (blocking async)"""
        import websockets  # live extra

        self.approval_key = get_approval_key(self.config)
        async with websockets.connect(self._ws_url, ping_interval=None) as ws:
            await ws.send(self._subscribe_frame())
            log.info("체결통보 구독 요청 전송 (%s)", self._tr_id)
            async for raw in ws:
                if self._is_pingpong(raw):
                    await ws.send(raw)  # 서버 PINGPONG 프레임 그대로 echo
                    continue
                try:
                    self._handle_frame(raw, on_execution)
                except Exception as e:  # 한 프레임 실패가 스트림을 끊지 않도록
                    log.error("체결통보 프레임 처리 실패: %s", e)
