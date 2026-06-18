#!/usr/bin/env python3
"""
Notion Contents DB + Google Drive → Instagram 콘텐츠 큐 준비 스크립트

아래 조건의 항목을 Notion Contents DB에서 조회합니다.
  - 유형: Instagram
  - 진행 상태: 아이디어 또는 진행 중

Google Drive Instagram 폴더의 이미지/영상을 제목 기준으로 매칭하여
이미지_URL, 형식 속성을 채운 뒤 진행 상태를 '진행 중'으로 업데이트합니다.
콘텐츠 담당자가 캡션·해시태그를 완성하고 진행 상태를 '검토 중'으로 바꾸면
notion_instagram_publish.py가 자동으로 게시합니다.

필요한 환경 변수:
  NOTION_API_KEY              - Notion 통합 API 키
  NOTION_DATABASE_ID          - Contents DB ID (기본값 내장)
  GOOGLE_DRIVE_INSTAGRAM_FOLDER - Instagram 폴더 ID (기본값 내장)
  GOOGLE_SERVICE_ACCOUNT_JSON - 서비스 계정 키 JSON 문자열
"""

import json
import os
import re
import sys
import logging
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_DATABASE_ID = os.environ.get(
    "NOTION_DATABASE_ID", "bbc28be1-3565-4c50-b353-4e6708c5e1ff"
)
# Google Drive Instagram 폴더 ID
GDRIVE_INSTAGRAM_FOLDER = os.environ.get(
    "GOOGLE_DRIVE_INSTAGRAM_FOLDER", "1pHBSTfTGpGLcrSkaTF6LyF7fkPlAMCq3"
)
# Google Drive API
GDRIVE_API_BASE = "https://www.googleapis.com/drive/v3"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}

# ---------------------------------------------------------------------------
# Notion API 헬퍼 (notion_instagram_publish.py 와 동일 패턴)
# ---------------------------------------------------------------------------

def _notion_request(method: str, path: str, api_key: str, body: dict | None = None) -> dict:
    url = f"{NOTION_BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API {method} {path} → {e.code}: {body_txt}") from e


def notion_query_database(database_id: str, api_key: str, filter_body: dict) -> list[dict]:
    results = []
    start_cursor = None
    while True:
        payload = {**filter_body, "page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        resp = _notion_request("POST", f"/databases/{database_id}/query", api_key, payload)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")
    return results


def notion_update_page(page_id: str, api_key: str, properties: dict) -> dict:
    return _notion_request("PATCH", f"/pages/{page_id}", api_key, {"properties": properties})

# ---------------------------------------------------------------------------
# Google Drive API 헬퍼 (OAuth2 서비스 계정)
# ---------------------------------------------------------------------------

def _get_access_token_from_service_account(sa_json: str) -> str:
    """서비스 계정 JSON에서 OAuth2 액세스 토큰을 발급합니다."""
    import base64
    import hmac
    import hashlib
    import struct

    try:
        sa = json.loads(sa_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"서비스 계정 JSON 파싱 실패: {e}") from e

    # JWT 생성
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()

    # RSA-SHA256 서명 (cryptography 라이브러리 필요)
    try:
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        private_key = serialization.load_pem_private_key(
            sa["private_key"].encode(), password=None
        )
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        jwt_token = f"{header_b64}.{payload_b64}.{b64url(signature)}"
    except ImportError:
        raise RuntimeError(
            "cryptography 패키지가 필요합니다: pip install cryptography"
        )

    # 토큰 교환
    token_data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["access_token"]


def gdrive_list_folder(folder_id: str, access_token: str) -> list[dict]:
    """Google Drive 폴더의 파일 목록을 반환합니다."""
    files = []
    page_token = None
    while True:
        params: dict = {
            "q": f"'{folder_id}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,mimeType,webViewLink)",
            "pageSize": 100,
        }
        if page_token:
            params["pageToken"] = page_token
        url = f"{GDRIVE_API_BASE}/files?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return files


def file_to_direct_url(file_id: str) -> str:
    """Google Drive 파일 ID를 직접 다운로드 URL로 변환합니다."""
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def detect_format(filename: str) -> str:
    """파일명으로 콘텐츠 형식을 추정합니다."""
    name = filename.lower()
    ext = Path(name).suffix
    if ext in VIDEO_EXTENSIONS:
        if "reel" in name:
            return "reel"
        if "story" in name:
            return "story"
        return "reel"
    if "carousel" in name or re.search(r"-\d{2}\.(jpg|jpeg|png)$", name):
        return "carousel"
    return "single_image"

# ---------------------------------------------------------------------------
# 제목 매칭
# ---------------------------------------------------------------------------

def normalize_title(title: str) -> str:
    """비교용 정규화 — 소문자, 특수문자 제거."""
    return re.sub(r"[^a-z0-9가-힣]", "", title.lower())


def match_files_to_page(page_title: str, drive_files: list[dict]) -> list[dict]:
    """Notion 페이지 제목과 Drive 파일명을 매칭합니다."""
    norm_title = normalize_title(page_title)
    matched = []
    for f in drive_files:
        norm_name = normalize_title(Path(f["name"]).stem)
        # 제목이 파일명에 포함되거나 파일명이 제목에 포함되면 매칭
        if norm_title in norm_name or norm_name in norm_title:
            matched.append(f)
    return matched

# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def run() -> None:
    notion_api_key = os.environ.get("NOTION_API_KEY", "").strip()
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

    if not notion_api_key:
        logger.error("NOTION_API_KEY 환경 변수가 없습니다.")
        sys.exit(1)

    # ── Notion: 아이디어/진행 중 Instagram 항목 조회 ─────────────────────────
    logger.info("Notion Contents DB 조회 중 (Instagram 아이디어/진행 중)...")
    filter_body = {
        "filter": {
            "and": [
                {"property": "유형", "select": {"equals": "Instagram"}},
                {
                    "or": [
                        {"property": "진행 상태", "status": {"equals": "아이디어"}},
                        {"property": "진행 상태", "status": {"equals": "진행 중"}},
                    ]
                },
                # 이미지_URL이 비어 있는 항목만 처리
                {"property": "이미지_URL", "url": {"is_empty": True}},
            ]
        }
    }
    pages = notion_query_database(NOTION_DATABASE_ID, notion_api_key, filter_body)
    logger.info("처리 대상 항목: %d개", len(pages))

    if not pages:
        logger.info("매칭할 항목이 없습니다.")
        return

    # ── Google Drive 파일 목록 ────────────────────────────────────────────────
    drive_files: list[dict] = []
    if sa_json:
        try:
            access_token = _get_access_token_from_service_account(sa_json)
            drive_files = gdrive_list_folder(GDRIVE_INSTAGRAM_FOLDER, access_token)
            logger.info("Google Drive Instagram 폴더 파일 수: %d개", len(drive_files))
        except Exception as exc:
            logger.warning("Google Drive 접근 실패 (건너뜀): %s", exc)
    else:
        logger.info("GOOGLE_SERVICE_ACCOUNT_JSON 미설정 — Drive 매칭 건너뜀")

    # 파일 확장자 기준 분류
    image_files = [f for f in drive_files if Path(f["name"]).suffix.lower() in IMAGE_EXTENSIONS]
    video_files = [f for f in drive_files if Path(f["name"]).suffix.lower() in VIDEO_EXTENSIONS]

    updated = 0
    for page in pages:
        page_id = page["id"]
        props = page.get("properties", {})
        title = "".join(
            t.get("plain_text", "") for t in props.get("제목", {}).get("title", [])
        )
        if not title:
            continue

        logger.info("── '%s' 처리 중...", title)
        props_to_update: dict = {}

        if drive_files:
            # 영상 우선 매칭
            video_matches = match_files_to_page(title, video_files)
            image_matches = match_files_to_page(title, image_files)

            if video_matches:
                f = video_matches[0]
                fmt = detect_format(f["name"])
                props_to_update["이미지_URL"] = {"url": file_to_direct_url(f["id"])}
                props_to_update["형식"] = {"select": {"name": fmt}}
                logger.info("  영상 매칭: %s → %s (%s)", f["name"], fmt, file_to_direct_url(f["id"]))
            elif len(image_matches) == 1:
                f = image_matches[0]
                props_to_update["이미지_URL"] = {"url": file_to_direct_url(f["id"])}
                props_to_update["형식"] = {"select": {"name": "single_image"}}
                logger.info("  이미지 매칭: %s", f["name"])
            elif len(image_matches) > 1:
                # carousel: 파일명 정렬 후 JSON 배열로 저장
                sorted_files = sorted(image_matches, key=lambda x: x["name"])
                urls = [file_to_direct_url(f["id"]) for f in sorted_files]
                props_to_update["이미지_URLs"] = {
                    "rich_text": [{"type": "text", "text": {"content": json.dumps(urls, ensure_ascii=False)}}]
                }
                props_to_update["형식"] = {"select": {"name": "carousel"}}
                logger.info("  carousel 매칭: %d장", len(urls))
            else:
                logger.info("  매칭된 파일 없음 — 수동 등록 필요")

        # 진행 상태 → 진행 중 (아이디어에서만)
        current_status = (props.get("진행 상태", {}).get("status") or {}).get("name", "")
        if current_status == "아이디어" and props_to_update:
            props_to_update["진행 상태"] = {"status": {"name": "진행 중"}}

        if props_to_update:
            notion_update_page(page_id, notion_api_key, props_to_update)
            logger.info("  Notion 업데이트 완료")
            updated += 1

    logger.info("완료 — %d개 업데이트됨", updated)


if __name__ == "__main__":
    run()
