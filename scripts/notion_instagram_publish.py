#!/usr/bin/env python3
"""
Notion → Instagram 자동 게시 스크립트

Notion Contents DB에서 다음 조건의 항목을 조회합니다.
  - 유형: Instagram
  - 진행 상태: 검토 중  (Approved 상태)
  - 게시일: 현재 시각 이전 (또는 미설정)

검증 → 캡션 품질 검토 → Instagram 게시 → Notion 상태 '게시 완료' 업데이트

필요한 환경 변수:
  NOTION_API_KEY         - Notion 통합 API 키
  NOTION_DATABASE_ID     - Contents 데이터베이스 ID (기본값 내장)
  INSTAGRAM_USER_ID      - Instagram 비즈니스 계정 ID
  INSTAGRAM_ACCESS_TOKEN - Meta Graph API 장기 액세스 토큰
"""

import json
import os
import re
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"
# Contents DB (유형=Instagram, 진행 상태=검토 중)
NOTION_DATABASE_ID = os.environ.get(
    "NOTION_DATABASE_ID", "bbc28be1-3565-4c50-b353-4e6708c5e1ff"
)

GRAPH_API_VERSION = os.environ.get("INSTAGRAM_GRAPH_API_VERSION", "v25.0")
MAX_CAPTION_LENGTH = 2200
MAX_HASHTAG_COUNT = 30
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
PUBLISHING_POLL_INTERVAL = 60

REPO_ROOT = Path(__file__).parent.parent
LOG_FILE = REPO_ROOT / "logs" / "notion_instagram_log.json"

# 브랜드 금지 표현
BANNED_EXPRESSIONS = [
    "업계 최저가", "가성비 영상", "빠른 납기 보장", "국내 최초", "세계 유일",
]
# CTA 키워드 (최소 하나 필요)
CTA_KEYWORDS = [
    "댓글", "DM", "링크", "프로필", "저장", "공유", "태그",
    "알려주세요", "보내주세요", "남겨주세요", "문의", "이어가",
]

# ---------------------------------------------------------------------------
# Notion REST API 헬퍼
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
    """페이지네이션을 처리하며 데이터베이스 전체 결과를 반환합니다."""
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


def notion_get_blocks(block_id: str, api_key: str) -> list[dict]:
    """페이지 블록(본문)을 모두 가져옵니다."""
    blocks = []
    start_cursor = None
    while True:
        path = f"/blocks/{block_id}/children?page_size=100"
        if start_cursor:
            path += f"&start_cursor={start_cursor}"
        resp = _notion_request("GET", path, api_key)
        blocks.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")
    return blocks


def notion_update_page(page_id: str, api_key: str, properties: dict) -> dict:
    """Notion 페이지 속성을 업데이트합니다."""
    return _notion_request("PATCH", f"/pages/{page_id}", api_key, {"properties": properties})


def notion_append_block(page_id: str, api_key: str, block: dict) -> dict:
    """페이지에 블록을 추가합니다."""
    return _notion_request(
        "POST", f"/blocks/{page_id}/children", api_key, {"children": [block]}
    )

# ---------------------------------------------------------------------------
# Notion 속성 파싱
# ---------------------------------------------------------------------------

def _rich_text_value(prop: dict) -> str:
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _title_value(prop: dict) -> str:
    return "".join(t.get("plain_text", "") for t in prop.get("title", []))


def parse_properties(page: dict) -> dict:
    """Notion 페이지 속성에서 필요한 값을 추출합니다."""
    props = page.get("properties", {})
    result = {}

    result["title"] = _title_value(props.get("제목", {}))
    result["type"] = (props.get("유형", {}).get("select") or {}).get("name", "")
    result["status"] = (props.get("진행 상태", {}).get("status") or {}).get("name", "")
    result["caption"] = _rich_text_value(props.get("캡션", {}))
    result["hashtags_raw"] = _rich_text_value(props.get("해시태그", {}))
    result["format"] = (props.get("형식", {}).get("select") or {}).get("name", "single_image")
    result["image_url"] = props.get("이미지_URL", {}).get("url", "") or ""
    result["image_urls_raw"] = _rich_text_value(props.get("이미지_URLs", {}))

    # 게시일 (예약 시간)
    date_prop = props.get("게시일", {}).get("date") or {}
    result["scheduled_time"] = date_prop.get("start", "")

    # 미디어 첨부 파일 (이미지_URL이 없을 때 fallback)
    media_files = []
    for f in props.get("미디어", {}).get("files", []):
        if f.get("type") == "external":
            media_files.append(f["external"]["url"])
        elif f.get("type") == "file":
            media_files.append(f["file"]["url"])
    result["media_files"] = media_files

    return result


def parse_page_body(blocks: list[dict]) -> dict:
    """페이지 본문에서 캡션, 해시태그, 이미지 URL, 형식을 파싱합니다.

    페이지 본문 권장 구조:
      ## 캡션
      [캡션 내용 — 여러 단락 가능]

      ## 해시태그
      #tag1 #tag2 #tag3

      ## 미디어
      https://drive.google.com/uc?export=download&id=FILE_ID
      (carousel는 URL을 줄바꿈으로 구분)

      ## 형식
      single_image  ← single_image / carousel / reel / story
    """
    sections: dict[str, list[str]] = {}
    current = None

    for block in blocks:
        btype = block.get("type", "")
        rt_key = btype if btype in block else None

        if btype == "heading_2":
            heading_text = "".join(
                t.get("plain_text", "") for t in block["heading_2"].get("rich_text", [])
            ).strip()
            current = heading_text
            sections.setdefault(current, [])
        elif current is not None and rt_key:
            text = "".join(
                t.get("plain_text", "") for t in block[rt_key].get("rich_text", [])
            ).strip()
            if text:
                sections[current].append(text)

    body: dict = {}
    if "캡션" in sections:
        body["caption"] = "\n\n".join(sections["캡션"])
    if "해시태그" in sections:
        raw = " ".join(sections["해시태그"])
        body["hashtags_raw"] = raw
    if "미디어" in sections:
        body["media_urls"] = [u.strip() for u in sections["미디어"] if u.strip()]
    if "형식" in sections and sections["형식"]:
        body["format"] = sections["형식"][0].strip()

    return body


def _gdrive_to_direct(url: str) -> str:
    """Google Drive 공유 링크를 직접 다운로드 URL로 변환합니다."""
    m = re.search(r"/file/d/([^/]+)", url)
    if not m:
        m = re.search(r"[?&]id=([^&]+)", url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def resolve_media_url(url: str) -> str:
    """Google Drive URL를 직접 접근 URL로 변환합니다."""
    if "drive.google.com" in url and "uc?export=download" not in url:
        return _gdrive_to_direct(url)
    return url

# ---------------------------------------------------------------------------
# 콘텐츠 항목 구성
# ---------------------------------------------------------------------------

def build_item(page: dict, api_key: str) -> dict:
    """Notion 페이지에서 게시 가능한 item dict를 구성합니다."""
    page_id = page["id"]
    props = parse_properties(page)

    # 페이지 본문에서 추가 정보 파싱
    blocks = notion_get_blocks(page_id, api_key)
    body = parse_page_body(blocks)

    # 캡션: 속성 우선, 없으면 본문
    caption = props["caption"] or body.get("caption", "")

    # 해시태그: 속성 우선, 없으면 본문, 없으면 캡션에서 추출
    hashtags_raw = props["hashtags_raw"] or body.get("hashtags_raw", "")
    if hashtags_raw:
        hashtags = re.findall(r"#\S+", hashtags_raw)
    else:
        hashtags = re.findall(r"#\S+", caption)
        caption = re.sub(r"\s*#\S+", "", caption).strip()

    # 형식
    fmt = props["format"] or body.get("format", "single_image")

    # 이미지 URL 결정
    image_url = props["image_url"]
    image_urls: list[str] = []

    if props["image_urls_raw"]:
        try:
            image_urls = json.loads(props["image_urls_raw"])
        except json.JSONDecodeError:
            image_urls = [u.strip() for u in props["image_urls_raw"].splitlines() if u.strip()]

    if not image_url and not image_urls:
        # 본문 미디어 URL
        body_media = body.get("media_urls", [])
        if len(body_media) == 1:
            image_url = body_media[0]
        elif len(body_media) > 1:
            image_urls = body_media
            fmt = "carousel"

    if not image_url and not image_urls:
        # Notion 첨부 파일 fallback
        if len(props["media_files"]) == 1:
            image_url = props["media_files"][0]
        elif len(props["media_files"]) > 1:
            image_urls = props["media_files"]
            fmt = "carousel"

    # Google Drive URL 변환
    if image_url:
        image_url = resolve_media_url(image_url)
    image_urls = [resolve_media_url(u) for u in image_urls]

    item = {
        "notion_page_id": page_id,
        "id": f"notion_{page_id.replace('-', '')[:16]}",
        "title": props["title"],
        "caption": caption,
        "hashtags": hashtags,
        "format": fmt,
        "scheduled_time": props["scheduled_time"],
    }

    if fmt == "carousel" and image_urls:
        item["image_urls"] = image_urls
    elif fmt == "reel":
        item["video_url"] = image_url
    elif fmt == "story":
        item["video_url"] = image_url if image_url.lower().endswith((".mp4", ".mov")) else ""
        if not item["video_url"]:
            item["image_url"] = image_url
    else:
        item["image_url"] = image_url

    return item

# ---------------------------------------------------------------------------
# 콘텐츠 검증
# ---------------------------------------------------------------------------

def validate_item(item: dict) -> list[str]:
    """콘텐츠 항목을 검증하고 오류 목록을 반환합니다."""
    errors = []
    fmt = item.get("format", "single_image")

    if fmt == "reel":
        video_url = item.get("video_url", "")
        if not video_url:
            errors.append("릴스 video_url이 없습니다.")
        else:
            ext = Path(urllib.parse.urlparse(video_url).path).suffix.lower()
            if ext not in ALLOWED_VIDEO_EXTENSIONS:
                errors.append(f"지원하지 않는 릴스 형식: {ext}")
    elif fmt == "story":
        if not item.get("image_url") and not item.get("video_url"):
            errors.append("스토리 image_url 또는 video_url이 없습니다.")
    elif fmt == "carousel":
        image_urls = item.get("image_urls", [])
        if not isinstance(image_urls, list) or not 2 <= len(image_urls) <= 10:
            errors.append("carousel image_urls는 2~10장이어야 합니다.")
        else:
            for url in image_urls:
                ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    errors.append(f"지원하지 않는 carousel 이미지 형식: {ext}")
    else:
        image_url = item.get("image_url", "")
        if not image_url:
            errors.append("image_url이 없습니다.")
        else:
            ext = Path(urllib.parse.urlparse(image_url).path).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                errors.append(f"지원하지 않는 이미지 형식: {ext}")

    caption = item.get("caption", "")
    if not caption:
        errors.append("캡션이 비어 있습니다.")
    elif len(caption) > MAX_CAPTION_LENGTH:
        errors.append(f"캡션 길이 초과: {len(caption)}자 (최대 {MAX_CAPTION_LENGTH}자)")

    hashtags = item.get("hashtags", [])
    if len(hashtags) > MAX_HASHTAG_COUNT:
        errors.append(f"해시태그 초과: {len(hashtags)}개 (최대 {MAX_HASHTAG_COUNT}개)")

    return errors


def review_caption_quality(caption: str, hashtags: list[str]) -> tuple[list[str], list[str]]:
    """캡션 품질을 검토합니다. (issues: 차단, warnings: 경고)"""
    issues: list[str] = []
    warnings: list[str] = []

    if not caption:
        return issues, warnings

    first_line = caption.split("\n")[0].strip()

    # 첫 문장 훅 검토
    if len(first_line) < 10:
        warnings.append(f"첫 줄이 너무 짧습니다 ({len(first_line)}자): '{first_line}'")
    elif not any(c in first_line for c in "?!,. ") or len(first_line.split()) < 3:
        warnings.append(f"첫 줄의 훅(관심 유발력)이 약합니다: '{first_line[:40]}'")

    # CTA 확인
    full_text = caption + " " + " ".join(hashtags)
    if not any(kw in full_text for kw in CTA_KEYWORDS):
        issues.append("CTA(Call To Action)가 없습니다. 댓글, DM, 링크 등의 유도 문구를 추가하세요.")

    # 브랜드 금지 표현 확인
    for expr in BANNED_EXPRESSIONS:
        if expr in caption:
            issues.append(f"금지된 브랜드 표현: '{expr}'")

    # 해시태그 수 권고
    if len(hashtags) < 3:
        warnings.append(f"해시태그가 적습니다: {len(hashtags)}개 (Instagram 5~7개 권장)")
    elif len(hashtags) > 7:
        warnings.append(f"해시태그가 많습니다: {len(hashtags)}개 (Instagram 5~7개 권장)")

    return issues, warnings

# ---------------------------------------------------------------------------
# Meta Graph API (Instagram)
# ---------------------------------------------------------------------------

def _resolve_api_base(token: str) -> str:
    if len(token) < 40:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN이 너무 짧습니다.")
    if token.startswith("IG"):
        return f"https://graph.instagram.com/{GRAPH_API_VERSION}"
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def _api_post(api_base: str, endpoint: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode("utf-8")
    url = f"{api_base}/{endpoint}"
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            err = RuntimeError(f"Meta API 오류 {e.code}: {body}")
            is_transient = '"is_transient":true' in body or '"code":2' in body
            if not is_transient or attempt == 4:
                raise err from e
            delay = 5 * (2 ** attempt)
            logger.warning("Meta 일시 오류 → %d초 후 재시도 (%d/5)", delay, attempt + 2)
            time.sleep(delay)
    raise RuntimeError("Meta API 재시도 초과")


def _api_get(api_base: str, endpoint: str, access_token: str, fields: str = "") -> dict:
    params: dict = {"access_token": access_token}
    if fields:
        params["fields"] = fields
    url = f"{api_base}/{endpoint}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            err = RuntimeError(f"Meta GET 오류 {e.code}: {body}")
            is_transient = '"is_transient":true' in body or '"code":2' in body
            if not is_transient or attempt == 4:
                raise err from e
            delay = 5 * (2 ** attempt)
            time.sleep(delay)
    raise RuntimeError("Meta API GET 재시도 초과")


def diagnose_access(api_base: str, access_token: str, configured_user_id: str) -> str:
    if "graph.facebook.com" in api_base:
        if not configured_user_id.isdigit():
            raise RuntimeError("Facebook Graph API 토큰에는 숫자 INSTAGRAM_USER_ID가 필요합니다.")
        profile = _api_get(api_base, configured_user_id, access_token, "id,username,media_count")
    else:
        profile = _api_get(api_base, "me", access_token, "id,user_id,username,account_type,media_count")

    resolved_id = str(profile.get("user_id") or profile.get("id") or "").strip()
    if not resolved_id.isdigit():
        raise RuntimeError("숫자 Instagram 계정 ID를 확인하지 못했습니다.")
    logger.info("계정 확인: username=%s, user_id=%s", profile.get("username"), resolved_id)
    return resolved_id


def wait_for_container(api_base: str, creation_id: str, access_token: str, timeout: int = 300) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = _api_get(api_base, creation_id, access_token, "status_code,status")
        code = result.get("status_code", "")
        if code in {"FINISHED", "PUBLISHED"}:
            return
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"컨테이너 처리 실패: {code} — {result.get('status', '')}")
        remaining = deadline - time.time()
        if remaining > 0:
            time.sleep(min(PUBLISHING_POLL_INTERVAL, remaining))
    raise RuntimeError(f"컨테이너가 {timeout}초 내에 준비되지 않았습니다.")


def create_image_container(api_base: str, user_id: str, access_token: str, image_url: str, caption: str) -> str:
    result = _api_post(api_base, f"{user_id}/media", {
        "image_url": image_url, "caption": caption, "access_token": access_token,
    })
    return result["id"]


def create_carousel_container(api_base: str, user_id: str, access_token: str, image_urls: list[str], caption: str) -> str:
    child_ids = []
    for url in image_urls:
        r = _api_post(api_base, f"{user_id}/media", {
            "image_url": url, "is_carousel_item": "true", "access_token": access_token,
        })
        wait_for_container(api_base, r["id"], access_token)
        child_ids.append(r["id"])
    result = _api_post(api_base, f"{user_id}/media", {
        "media_type": "CAROUSEL", "children": ",".join(child_ids),
        "caption": caption, "access_token": access_token,
    })
    return result["id"]


def _rupload(api_base: str, creation_id: str, access_token: str, video_url: str) -> None:
    upload_uri = (
        f"https://rupload.facebook.com/ig-api-upload/{GRAPH_API_VERSION}/{creation_id}"
    )
    for attempt in range(5):
        req = urllib.request.Request(
            upload_uri, data=b"",
            headers={"Authorization": f"OAuth {access_token}", "file_url": video_url},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                r = json.loads(resp.read())
                if not r.get("success"):
                    raise RuntimeError(f"영상 업로드 실패: {r}")
                return
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            err = RuntimeError(f"영상 업로드 오류 {e.code}: {body}")
            if '"retriable":true' not in body and attempt == 4:
                raise err from e
            time.sleep(5 * (2 ** attempt))
    raise RuntimeError("영상 업로드 재시도 초과")


def create_reel_container(api_base: str, user_id: str, access_token: str, video_url: str, caption: str) -> str:
    r = _api_post(api_base, f"{user_id}/media", {
        "media_type": "REELS", "upload_type": "resumable",
        "caption": caption, "share_to_feed": "true", "access_token": access_token,
    })
    creation_id = r["id"]
    _rupload(api_base, creation_id, access_token, video_url)
    return creation_id


def create_story_container(api_base: str, user_id: str, access_token: str, image_url: str = "", video_url: str = "") -> str:
    if video_url:
        r = _api_post(api_base, f"{user_id}/media", {
            "media_type": "STORIES", "upload_type": "resumable", "access_token": access_token,
        })
        creation_id = r["id"]
        _rupload(api_base, creation_id, access_token, video_url)
        return creation_id
    r = _api_post(api_base, f"{user_id}/media", {
        "media_type": "STORIES", "image_url": image_url, "access_token": access_token,
    })
    return r["id"]


def publish_container(api_base: str, user_id: str, access_token: str, creation_id: str) -> str:
    last_err: Exception | None = None
    for attempt in range(5):
        if attempt:
            time.sleep(10)
        try:
            r = _api_post(api_base, f"{user_id}/media_publish", {
                "creation_id": creation_id, "access_token": access_token,
            })
            return r["id"]
        except RuntimeError as exc:
            last_err = exc
            if "9007" not in str(exc) and "not ready" not in str(exc):
                raise
    raise last_err  # type: ignore[misc]


def get_permalink(api_base: str, post_id: str, access_token: str) -> str:
    params = urllib.parse.urlencode({"fields": "permalink", "access_token": access_token})
    try:
        with urllib.request.urlopen(f"{api_base}/{post_id}?{params}", timeout=30) as resp:
            return json.loads(resp.read()).get("permalink", f"https://www.instagram.com/p/{post_id}/")
    except Exception:
        return f"https://www.instagram.com/p/{post_id}/"


def build_full_caption(caption: str, hashtags: list[str]) -> str:
    tag_str = " ".join(hashtags)
    return f"{caption}\n\n{tag_str}" if tag_str else caption

# ---------------------------------------------------------------------------
# 로그
# ---------------------------------------------------------------------------

def append_log(entry: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logs: list = []
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = json.load(f)
    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Notion 상태 업데이트
# ---------------------------------------------------------------------------

def mark_published(page_id: str, api_key: str, post_id: str, post_url: str, posted_at: str) -> None:
    """Notion 페이지를 '게시 완료'로 업데이트하고 게시 정보를 기록합니다."""
    props: dict = {
        "진행 상태": {"status": {"name": "게시 완료"}},
        "링크": {"url": post_url},
        "게시일": {"date": {"start": posted_at}},
        "게시_ID": {"rich_text": [{"type": "text", "text": {"content": post_id}}]},
    }
    notion_update_page(page_id, api_key, props)


def mark_invalid(page_id: str, api_key: str, errors: list[str]) -> None:
    """검증 실패 항목에 오류 내용을 본문에 기록합니다."""
    error_text = "검증 실패:\n" + "\n".join(f"- {e}" for e in errors)
    notion_append_block(page_id, api_key, {
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": error_text}}],
            "icon": {"type": "emoji", "emoji": "⚠️"},
            "color": "red_background",
        },
    })

# ---------------------------------------------------------------------------
# 예약 시간 확인
# ---------------------------------------------------------------------------

def is_due(scheduled_time_str: str, now: datetime) -> bool:
    if not scheduled_time_str:
        return True  # 예약 시간이 없으면 즉시 게시
    try:
        dt = datetime.fromisoformat(scheduled_time_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= now
    except ValueError:
        logger.warning("예약 시간 파싱 실패: %s", scheduled_time_str)
        return False

# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def run() -> None:
    notion_api_key = os.environ.get("NOTION_API_KEY", "").strip()
    user_id_env = os.environ.get("INSTAGRAM_USER_ID", "").strip()
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()

    if not notion_api_key:
        logger.error("NOTION_API_KEY 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    if not access_token:
        logger.error("INSTAGRAM_ACCESS_TOKEN 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    api_base = _resolve_api_base(access_token)
    logger.info("Meta API 호스트: %s", api_base)

    user_id = diagnose_access(api_base, access_token, user_id_env)
    now = datetime.now(tz=timezone.utc)

    # ── Notion 조회 ──────────────────────────────────────────────────────────
    logger.info("Notion Contents DB 조회 중... (유형=Instagram, 진행 상태=검토 중)")
    filter_body = {
        "filter": {
            "and": [
                {"property": "유형", "select": {"equals": "Instagram"}},
                {"property": "진행 상태", "status": {"equals": "검토 중"}},
            ]
        },
        "sorts": [{"property": "게시일", "direction": "ascending"}],
    }
    pages = notion_query_database(NOTION_DATABASE_ID, notion_api_key, filter_body)
    logger.info("조회된 Instagram 항목: %d개", len(pages))

    if not pages:
        logger.info("게시 대기 중인 항목이 없습니다.")
        return

    published_count = 0
    skipped_count = 0

    for page in pages:
        page_id = page["id"]
        logger.info("── 항목 처리 중: %s", page_id)

        try:
            item = build_item(page, notion_api_key)
        except Exception as exc:
            logger.error("[%s] 항목 구성 실패: %s", page_id, exc)
            skipped_count += 1
            continue

        item_id = item["id"]
        title = item.get("title", "제목 없음")
        logger.info("[%s] 제목: %s", item_id, title)

        # ── 예약 시간 확인 ──────────────────────────────────────────────────
        scheduled = item.get("scheduled_time", "")
        if not is_due(scheduled, now):
            logger.info("[%s] 예약 시간 미도래: %s", item_id, scheduled)
            skipped_count += 1
            continue

        # ── 유효성 검사 ─────────────────────────────────────────────────────
        errors = validate_item(item)
        if errors:
            logger.warning("[%s] 검증 실패: %s", item_id, " | ".join(errors))
            mark_invalid(page_id, notion_api_key, errors)
            append_log({
                "id": item_id, "notion_page_id": page_id, "title": title,
                "status": "invalid", "errors": errors, "timestamp": now.isoformat(),
            })
            skipped_count += 1
            continue

        # ── 캡션 품질 검토 ──────────────────────────────────────────────────
        caption = item.get("caption", "")
        hashtags = item.get("hashtags", [])
        quality_issues, quality_warnings = review_caption_quality(caption, hashtags)

        for w in quality_warnings:
            logger.warning("[%s] 캡션 경고: %s", item_id, w)

        if quality_issues:
            logger.warning("[%s] 캡션 품질 문제 (차단): %s", item_id, " | ".join(quality_issues))
            mark_invalid(page_id, notion_api_key, quality_issues)
            append_log({
                "id": item_id, "notion_page_id": page_id, "title": title,
                "status": "caption_invalid", "errors": quality_issues,
                "timestamp": now.isoformat(),
            })
            skipped_count += 1
            continue

        # ── Instagram 게시 ──────────────────────────────────────────────────
        full_caption = build_full_caption(caption, hashtags)
        fmt = item.get("format", "single_image")

        try:
            logger.info("[%s] 미디어 컨테이너 생성 중 (형식: %s)...", item_id, fmt)
            if fmt == "reel":
                creation_id = create_reel_container(
                    api_base, user_id, access_token, item["video_url"], full_caption
                )
            elif fmt == "story":
                creation_id = create_story_container(
                    api_base, user_id, access_token,
                    item.get("image_url", ""), item.get("video_url", ""),
                )
            elif fmt == "carousel":
                creation_id = create_carousel_container(
                    api_base, user_id, access_token, item["image_urls"], full_caption
                )
            else:  # single_image
                creation_id = create_image_container(
                    api_base, user_id, access_token, item["image_url"], full_caption
                )

            logger.info("[%s] 미디어 처리 완료 대기...", item_id)
            wait_for_container(api_base, creation_id, access_token, timeout=300)

            logger.info("[%s] Instagram 게시 중...", item_id)
            post_id = publish_container(api_base, user_id, access_token, creation_id)
            permalink = get_permalink(api_base, post_id, access_token)
            posted_at = datetime.now(tz=timezone.utc).isoformat()

            logger.info("[%s] 게시 완료: %s", item_id, permalink)

            # ── Notion 업데이트 ─────────────────────────────────────────────
            mark_published(page_id, notion_api_key, post_id, permalink, posted_at)
            logger.info("[%s] Notion 상태 → 게시 완료", item_id)

            append_log({
                "id": item_id, "notion_page_id": page_id, "title": title,
                "status": "published", "post_id": post_id, "post_url": permalink,
                "format": fmt, "timestamp": posted_at,
            })
            published_count += 1

        except Exception as exc:
            logger.error("[%s] 게시 실패: %s", item_id, exc)
            append_log({
                "id": item_id, "notion_page_id": page_id, "title": title,
                "status": "failed", "error": str(exc), "timestamp": now.isoformat(),
            })

    logger.info("완료 — 게시: %d개, 건너뜀: %d개", published_count, skipped_count)


if __name__ == "__main__":
    run()
