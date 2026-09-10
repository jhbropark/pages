import pytest

from quantbot.execution.kis_websocket import (
    KISWebSocketClient,
    aes_cbc_decrypt,
    parse_execution_notice,
)
from quantbot.config import KISConfig


def test_parse_execution_notice_buy_filled():
    # 필드 레이아웃 순서대로 (^ 구분). 4=side(02 매수), 8=ticker, 9=qty, 10=price, 13=exec_yn(2 체결)
    fields = [
        "CUST1", "12345678-01", "0001", "0000", "02", "0", "00", "0",
        "005930", "10", "70000", "093015", "0", "2", "0", "00",
        "10", "홍길동", "삼성전자", "00", "",
    ]
    notice = parse_execution_notice("^".join(fields))
    assert notice["ticker"] == "005930"
    assert notice["exec_qty"] == "10"
    assert notice["exec_price"] == "70000"
    assert notice["side_label"] == "buy"
    assert notice["is_filled"] is True


def test_parse_execution_notice_sell_accepted_not_filled():
    fields = ["C", "A", "1", "0", "01", "0", "00", "0", "000660",
              "0", "0", "0900", "0", "1", "1", "00"]  # exec_yn=1 (접수)
    notice = parse_execution_notice("^".join(fields))
    assert notice["side_label"] == "sell"
    assert notice["is_filled"] is False


def test_tr_id_and_ws_url_switch_by_env():
    paper = KISWebSocketClient(KISConfig(env="paper", account_no="1-01"))
    real = KISWebSocketClient(KISConfig(env="real", account_no="1-01"))
    assert paper._tr_id == "H0STCNI9"
    assert real._tr_id == "H0STCNI0"
    assert "31000" in paper._ws_url
    assert "21000" in real._ws_url


def test_handle_frame_dispatches_filled_execution():
    client = KISWebSocketClient(KISConfig(env="paper", account_no="1-01"))
    got = []
    fields = ["C", "A", "1", "0", "02", "0", "00", "0", "005930",
              "5", "71000", "0930", "0", "2", "0", "00"]
    raw = "0|H0STCNI9|001|" + "^".join(fields)  # 평문(암호화 키 미설정)
    client._handle_frame(raw, got.append)
    assert len(got) == 1 and got[0]["ticker"] == "005930"


def test_subscribe_response_captures_aes_key():
    import json

    client = KISWebSocketClient(KISConfig(env="paper", account_no="1-01"))
    resp = json.dumps(
        {"header": {"tr_id": "H0STCNI9"},
         "body": {"rt_cd": "0",
                  "output": {"key": "0123456789ABCDEF0123456789ABCDEF", "iv": "0123456789ABCDEF"}}}
    )
    client._handle_frame(resp, lambda n: None)
    assert client._aes_key == "0123456789ABCDEF0123456789ABCDEF"
    assert client._aes_iv == "0123456789ABCDEF"


def test_aes_cbc_roundtrip():
    Crypto = pytest.importorskip("Crypto")  # pycryptodome (live extra)
    import base64

    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad

    key = "0123456789ABCDEF0123456789ABCDEF"  # 32B
    iv = "0123456789ABCDEF"                    # 16B
    plaintext = "005930^10^70000"
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
    ct = base64.b64encode(cipher.encrypt(pad(plaintext.encode(), AES.block_size))).decode()
    assert aes_cbc_decrypt(key, iv, ct) == plaintext
