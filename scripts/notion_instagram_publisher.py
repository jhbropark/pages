#!/usr/bin/env python3
"""
Notion Content Queue → Instagram 자동 게시 스크립트

Notion "Content Queue" 데이터베이스에서 승인된 Instagram 콘텐츠를 조회해
Meta Graph API로 게시하고, 결과(게시 URL·ID·일시)를 Notion에 기록합니다.

필요한 환경 변수:
  NOTION_API_TOKEN       - Notion Internal Integration Token (ntn_... 또는 secret_...)
  INSTAGRAM_USER_ID      - Instagram 비즈니스 계정 숫자 ID
  INSTAGRAM_ACCESS_TOKEN - Meta Graph API 장기 액세스 토큰 (EAA... 또는 IGAA...)

Content Queue 데이터베이스 필드:
  제목         - 콘텐츠 제목                       (title)
  게시 채널     - Instagram / Facebook / LinkedIn  (select)
  상태          - Draft / Approved / Published / Failed  (select)
  게시 예정일   - 게시 예정 날짜(또는 날짜+시각)    (date)
  본문          - 캡션 텍스트                       (text/rich_text)
  해시태그      - 공백·줄바꿈으로 구분된 #태그 목록   (text/rich_text)
  이미지 URL    - 공개 URL, 캐러셀은 줄바꿈으로 구분  (text/rich_text)
  포맷          - single_image / carousel / reel / story  (select)
  게시 URL      - (게시 후 자동 기록)               (url)
  게시 ID       - (게시 후 자동 기록)               (text/rich_text)
  게시 일시     - (게시 후 자동 기록)               (date)
  오류 내용     - (실패 시 자동 기록)               (text/rich_text)
"""

import json
import os
import re
import sys
import time
import logging
from datetime import datetime, timezone, date as date_type
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
CONTENT_QUEUE_DB_ID = "9ea1f439-3860-471e-8663-8a2ba4ab1024"
NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"

REPO_ROOT = Path(__file__).parent.parent
LOG_FILE = REPO_ROOT / "logs" / "notion_instagram_log.json"

MAX_CAPTION_LENGTH = 2200
MAX_HASHTAG_COUNT = 30
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}

GRAPH_API_VERSION = os.environ.get("INSTAGRAM_GRAPH_API_VERSION", "v25.0")
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
PUBLISHING_POLL_INTERVAL = 60

CTA_KEYWORDS = [
    "댓글", "dm", "저장", "팔로우", "링크", "문의", "알려주세요", "보내주세요",
    "comment", "follow", "save", "share", "tag", "contact", "link",
    "클릭", "확인", "신청",
]

# ---------------------------------------------------------------------------
# 로깅
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notion REST API 헬퍼
# ---------------------------------------------------------------------------

def _notion_request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    """Notion API에 요청을 보내고 JSON 응답을 반환합니다."""
    url = f"{NOTION_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API 오류 {exc.code}: {body_text}") from exc


def query_approved_instagram_items(token: str) -> list[dict]:
    """Notion Content Queue에서 게시 대기 중인 Instagram 항목을 조회합니다."""
    filter_body = {
        "filter": {
            "and": [
                {
                    "property": "게시 채널",
                    "select": {"equals": "Instagram"},
                },
                {
                    "property": "상태",
                    "select": {"equals": "Approved"},
                },
            ]
        },
        "sorts": [{"property": "게시 예정일", "direction": "ascending"}],
        "page_size": 50,
    }
    result = _notion_request(
        "POST", f"/databases/{CONTENT_QUEUE_DB_ID}/query", token, filter_body
    )
    return result.get("results", [])


def update_notion_page(page_id: str, token: str, properties: dict) -> None:
    """Notion 페이지 속성을 업데이트합니다."""
    _notion_request("PATCH", f"/pages/{page_id}", token, {"properties": properties})


# ---------------------------------------------------------------------------
# 속성 추출 헬퍼
# ---------------------------------------------------------------------------

def _rich_text_value(prop: dict) -> str:
    """rich_text 또는 title 속성에서 plain_text를 추출합니다."""
    ptype = prop.get("type", "")
    items = prop.get(ptype, []) if ptype in ("rich_text", "title") else []
    return "".join(item.get("plain_text", "") for item in items)


def get_text(page: dict, prop_name: str) -> str:
    return _rich_text_value(page.get("properties", {}).get(prop_name, {}))


def get_select(page: dict, prop_name: str) -> str:
    prop = page.get("properties", {}).get(prop_name, {})
    sel = prop.get("select") or {}
    return sel.get("name", "")


def get_date_str(page: dict, prop_name: str) -> str:
    """date 속성의 start 값을 반환합니다 (ISO-8601 문자열)."""
    prop = page.get("properties", {}).get(prop_name, {})
    d = prop.get("date") or {}
    return d.get("start", "")


# ---------------------------------------------------------------------------
# 콘텐츠 파싱
# ---------------------------------------------------------------------------

def parse_image_urls(raw: str) -> list[str]:
    """줄바꿈으로 구분된 URL 텍스트에서 URL 목록을 반환합니다."""
    return [u.strip() for u in raw.strip().splitlines() if u.strip()]


def parse_hashtags(raw: str) -> list[str]:
    """해시태그 텍스트에서 #태그 목록을 추출합니다."""
    tags = re.findall(r'#\S+', raw)
    if not tags:
        # '#' 없이 쉼표·공백으로 구분된 경우
        words = [w.strip().lstrip("#") for w in re.split(r"[,\s]+", raw) if w.strip()]
        tags = [f"#{w}" for w in words if w]
    return tags


def is_due(scheduled_str: str, now: datetime) -> bool:
    """게시 예정 시각이 현재보다 같거나 이전인지 확인합니다."""
    if not scheduled_str:
        return False
    try:
        dt = datetime.fromisoformat(scheduled_str)
    except ValueError:
        return False
    # 날짜만 있는 경우 (YYYY-MM-DD) → 당일 00:00 UTC로 간주
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt <= now


# ---------------------------------------------------------------------------
# 유효성 검사
# ---------------------------------------------------------------------------

def validate_content(
    fmt: str,
    image_urls: list[str],
    caption: str,
    hashtags: list[str],
    scheduled_str: str,
) -> list[str]:
    """콘텐츠 항목을 검증하고 오류 메시지 목록을 반환합니다."""
    errors = []

    if not scheduled_str:
        errors.append("게시 예정일이 없습니다.")

    if not caption:
        errors.append("본문(캡션)이 없습니다.")
    elif len(caption) > MAX_CAPTION_LENGTH:
        errors.append(f"캡션이 너무 깁니다: {len(caption)}자 (최대 {MAX_CAPTION_LENGTH}자)")

    if len(hashtags) > MAX_HASHTAG_COUNT:
        errors.append(f"해시태그가 너무 많습니다: {len(hashtags)}개 (최대 {MAX_HASHTAG_COUNT}개)")

    if fmt in ("single_image", ""):
        if not image_urls:
            errors.append("이미지 URL이 없습니다.")
        else:
            ext = Path(urllib.parse.urlparse(image_urls[0]).path).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                errors.append(f"지원하지 않는 이미지 형식: {ext}")

    elif fmt == "carousel":
        if len(image_urls) < 2:
            errors.append("캐러셀은 2개 이상의 이미지 URL이 필요합니다.")
        elif len(image_urls) > 10:
            errors.append("캐러셀은 최대 10개 이미지까지 허용됩니다.")
        for url in image_urls:
            ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                errors.append(f"지원하지 않는 캐러셀 이미지 형식: {ext} — {url}")

    elif fmt == "reel":
        if not image_urls:
            errors.append("릴스 동영상 URL이 없습니다.")
        else:
            ext = Path(urllib.parse.urlparse(image_urls[0]).path).suffix.lower()
            if ext not in ALLOWED_VIDEO_EXTENSIONS:
                errors.append(f"지원하지 않는 릴스 형식: {ext}")

    elif fmt == "story":
        if not image_urls:
            errors.append("스토리 이미지/동영상 URL이 없습니다.")
        else:
            ext = Path(urllib.parse.urlparse(image_urls[0]).path).suffix.lower()
            allowed = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
            if ext not in allowed:
                errors.append(f"지원하지 않는 스토리 형식: {ext}")

    return errors


# ---------------------------------------------------------------------------
# 캡션 품질 검토
# ---------------------------------------------------------------------------

def review_caption_quality(caption: str, title: str) -> None:
    """캡션 품질을 검토하고 경고를 로그에 기록합니다 (게시 차단 없음)."""
    lines = [l for l in caption.strip().splitlines() if l.strip()]
    first_line = lines[0] if lines else ""

    # 1. 후킹 첫 문장 확인
    has_hook = (
        "?" in first_line
        or "？" in first_line
        or any(ch.isdigit() for ch in first_line[:8])
        or len(first_line) <= 35
    )
    if not has_hook:
        logger.warning(
            "[%s] 캡션 품질: 첫 문장이 길거나 후킹이 약합니다 → \"%s\"",
            title, first_line[:50],
        )

    # 2. CTA 확인
    caption_lower = caption.lower()
    has_cta = any(kw in caption_lower for kw in CTA_KEYWORDS)
    if not has_cta:
        logger.warning("[%s] 캡션 품질: CTA(행동 유도 문구)가 없습니다.", title)

    # 3. 과도한 이모지 확인 (브랜드 전문성)
    emoji_count = sum(1 for c in caption if ord(c) > 0x1F000)
    if emoji_count > 6:
        logger.warning(
            "[%s] 캡션 품질: 이모지 과다 (%d개). 3개 이하를 권장합니다.",
            title, emoji_count,
        )

    if has_hook and has_cta:
        logger.info("[%s] 캡션 품질: 후킹 문장 ✓, CTA ✓", title)


# ---------------------------------------------------------------------------
# Meta Graph API
# ---------------------------------------------------------------------------

def _resolve_api_base(token: str) -> str:
    if token.isdigit():
        raise ValueError(
            "INSTAGRAM_ACCESS_TOKEN에 숫자 ID가 저장되어 있습니다. "
            "액세스 토큰 전체 문자열을 저장하고, 숫자 ID는 INSTAGRAM_USER_ID에 저장하세요."
        )
    if len(token) < 40:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN이 너무 짧습니다.")
    if token.startswith("IG"):
        return f"https://graph.instagram.com/{GRAPH_API_VERSION}"
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def _api_post(endpoint: str, params: dict, api_base: str) -> dict:
    data = urllib.parse.urlencode(params).encode("utf-8")
    url = f"{api_base}/{endpoint}"
    last_error = None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"API 오류 {exc.code}: {body}")
            is_transient = '"is_transient":true' in body or '"code":2' in body
            if not is_transient or attempt == 4:
                raise last_error from exc
            delay = 5 * (2 ** attempt)
            logger.warning("Meta 일시 오류, %d초 후 재시도 (%d/5).", delay, attempt + 2)
            time.sleep(delay)
    raise last_error


def _api_get(endpoint: str, access_token: str, api_base: str, fields: str = "") -> dict:
    params: dict = {"access_token": access_token}
    if fields:
        params["fields"] = fields
    url = f"{api_base}/{endpoint}?{urllib.parse.urlencode(params)}"
    last_error = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"API 조회 오류 {exc.code}: {body}")
            if '"code":2' not in body or attempt == 4:
                raise last_error from exc
            time.sleep(5 * (2 ** attempt))
    raise last_error


def _rupload_from_url(upload_uri: str, access_token: str, video_url: str) -> None:
    last_error = None
    for attempt in range(5):
        req = urllib.request.Request(
            upload_uri,
            data=b"",
            headers={"Authorization": f"OAuth {access_token}", "file_url": video_url},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                if not result.get("success"):
                    raise RuntimeError(f"Meta 영상 업로드 실패: {result}")
                return
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Meta 영상 업로드 오류 {exc.code}: {body}")
            is_transient = '"retriable":true' in body or '"is_transient":true' in body
            if not is_transient or attempt == 4:
                raise last_error from exc
            time.sleep(5 * (2 ** attempt))
    raise last_error


def _wait_for_container(creation_id: str, access_token: str, api_base: str, timeout: int = 300) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = _api_get(creation_id, access_token, api_base, "status_code,status")
        code = result.get("status_code", "")
        if code in {"FINISHED", "PUBLISHED"}:
            return
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(
                f"미디어 컨테이너 처리 실패 (id={creation_id}, code={code}, "
                f"status={result.get('status', '')})"
            )
        remaining = deadline - time.time()
        if remaining > 0:
            time.sleep(min(PUBLISHING_POLL_INTERVAL, remaining))
    raise RuntimeError(f"미디어 컨테이너가 {timeout}초 내에 준비되지 않았습니다.")


def _create_resumable_video(
    user_id: str, access_token: str, api_base: str,
    media_type: str, video_url: str, caption: str = "", share_to_feed: bool = False,
) -> str:
    params: dict = {
        "media_type": media_type,
        "upload_type": "resumable",
        "access_token": access_token,
    }
    if caption:
        params["caption"] = caption
    if media_type == "REELS":
        params["share_to_feed"] = "true" if share_to_feed else "false"
    result = _api_post(f"{user_id}/media", params, api_base)
    creation_id = result["id"]
    upload_uri = result.get("uri") or (
        f"https://rupload.facebook.com/ig-api-upload/{GRAPH_API_VERSION}/{creation_id}"
    )
    _rupload_from_url(upload_uri, access_token, video_url)
    return creation_id


def build_full_caption(caption: str, hashtags: list[str]) -> str:
    tag_str = " ".join(hashtags)
    return f"{caption}\n\n{tag_str}" if tag_str else caption


def publish_item(
    user_id: str,
    access_token: str,
    api_base: str,
    fmt: str,
    image_urls: list[str],
    full_caption: str,
) -> str:
    """콘텐츠를 Instagram에 게시하고 creation_id를 반환합니다."""
    if fmt == "reel":
        creation_id = _create_resumable_video(
            user_id, access_token, api_base, "REELS",
            image_urls[0], full_caption, share_to_feed=True,
        )
    elif fmt == "story":
        video_ext = Path(urllib.parse.urlparse(image_urls[0]).path).suffix.lower()
        if video_ext in ALLOWED_VIDEO_EXTENSIONS:
            creation_id = _create_resumable_video(
                user_id, access_token, api_base, "STORIES", image_urls[0]
            )
        else:
            result = _api_post(
                f"{user_id}/media",
                {"media_type": "STORIES", "image_url": image_urls[0], "access_token": access_token},
                api_base,
            )
            creation_id = result["id"]
    elif fmt == "carousel":
        child_ids = []
        for url in image_urls:
            r = _api_post(
                f"{user_id}/media",
                {"image_url": url, "is_carousel_item": "true", "access_token": access_token},
                api_base,
            )
            cid = r["id"]
            _wait_for_container(cid, access_token, api_base)
            child_ids.append(cid)
        result = _api_post(
            f"{user_id}/media",
            {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": full_caption,
                "access_token": access_token,
            },
            api_base,
        )
        creation_id = result["id"]
    else:  # single_image
        result = _api_post(
            f"{user_id}/media",
            {"image_url": image_urls[0], "caption": full_caption, "access_token": access_token},
            api_base,
        )
        creation_id = result["id"]

    return creation_id


def publish_media(user_id: str, access_token: str, api_base: str, creation_id: str) -> str:
    """미디어 컨테이너를 게시하고 post_id를 반환합니다."""
    last_error: Exception | None = None
    for attempt in range(5):
        if attempt:
            time.sleep(10)
        try:
            result = _api_post(
                f"{user_id}/media_publish",
                {"creation_id": creation_id, "access_token": access_token},
                api_base,
            )
            return result["id"]
        except RuntimeError as exc:
            last_error = exc
            if "9007" not in str(exc) and "not ready" not in str(exc):
                raise
    raise last_error


def get_permalink(post_id: str, access_token: str, api_base: str) -> str:
    try:
        data = _api_get(post_id, access_token, api_base, "permalink")
        return data.get("permalink", f"https://www.instagram.com/p/{post_id}/")
    except Exception:
        return f"https://www.instagram.com/p/{post_id}/"


def diagnose_access(access_token: str, configured_user_id: str, api_base: str) -> str:
    """토큰을 확인하고 실제 Instagram 계정 ID를 반환합니다."""
    if api_base.startswith("https://graph.facebook.com"):
        if not configured_user_id.isdigit():
            raise RuntimeError("Facebook Graph API 토큰에는 숫자 INSTAGRAM_USER_ID가 필요합니다.")
        profile = _api_get(configured_user_id, access_token, api_base, "id,username,media_count")
    else:
        profile = _api_get("me", access_token, api_base, "id,user_id,username,account_type,media_count")
    resolved_id = str(profile.get("user_id") or profile.get("id") or "").strip()
    if not resolved_id.isdigit():
        raise RuntimeError("토큰에서 숫자 Instagram 계정 ID를 확인하지 못했습니다.")
    logger.info(
        "토큰 계정 확인: username=%s, account_type=%s, user_id=%s",
        profile.get("username", "?"), profile.get("account_type", "?"), resolved_id,
    )
    return resolved_id


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
# 메인 로직
# ---------------------------------------------------------------------------

def run() -> None:
    notion_token = os.environ.get("NOTION_API_TOKEN", "").strip()
    user_id_env = os.environ.get("INSTAGRAM_USER_ID", "").strip()
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()

    if not notion_token:
        logger.error("NOTION_API_TOKEN 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    if not access_token:
        logger.error("INSTAGRAM_ACCESS_TOKEN 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    global GRAPH_API_BASE
    GRAPH_API_BASE = _resolve_api_base(access_token)
    logger.info("Instagram API 호스트: %s", GRAPH_API_BASE)

    user_id = diagnose_access(access_token, user_id_env, GRAPH_API_BASE)

    # ── 1. Notion에서 승인된 Instagram 항목 조회 ──────────────────────────
    logger.info("Notion Content Queue 조회 중 (채널=Instagram, 상태=Approved)...")
    pages = query_approved_instagram_items(notion_token)
    logger.info("조회된 항목: %d개", len(pages))

    now = datetime.now(tz=timezone.utc)
    published_count = 0

    for page in pages:
        page_id = page["id"]
        title = get_text(page, "제목") or f"(제목 없음) [{page_id[:8]}]"

        # ── 2. 게시 예정 시각 확인 ────────────────────────────────────────
        scheduled_str = get_date_str(page, "게시 예정일")
        if not is_due(scheduled_str, now):
            logger.info("[%s] 아직 게시 예정 시각이 아닙니다: %s", title, scheduled_str)
            continue

        logger.info("[%s] 처리 시작 (게시 예정일: %s)", title, scheduled_str)

        # ── 3. 필드 파싱 ──────────────────────────────────────────────────
        caption = get_text(page, "본문").strip()
        hashtag_raw = get_text(page, "해시태그").strip()
        hashtags = parse_hashtags(hashtag_raw) if hashtag_raw else []
        image_url_raw = get_text(page, "이미지 URL").strip()
        image_urls = parse_image_urls(image_url_raw)
        fmt = get_select(page, "포맷") or "single_image"

        # ── 4. 유효성 검사 ────────────────────────────────────────────────
        errors = validate_content(fmt, image_urls, caption, hashtags, scheduled_str)
        if errors:
            logger.warning("[%s] 유효성 검사 실패:\n  %s", title, "\n  ".join(errors))
            update_notion_page(page_id, notion_token, {
                "상태": {"select": {"name": "Failed"}},
                "오류 내용": {"rich_text": [{"type": "text", "text": {"content": "; ".join(errors)}}]},
            })
            append_log({
                "notion_page_id": page_id,
                "title": title,
                "status": "invalid",
                "errors": errors,
                "timestamp": now.isoformat(),
            })
            continue

        # ── 5. 캡션 품질 검토 (경고만, 게시 차단 없음) ───────────────────
        review_caption_quality(caption, title)

        if not hashtags:
            logger.warning("[%s] 해시태그가 없습니다. 게시는 계속 진행합니다.", title)

        # ── 6. 게시 ───────────────────────────────────────────────────────
        full_caption = build_full_caption(caption, hashtags)
        try:
            logger.info("[%s] 미디어 컨테이너 생성 중... (포맷: %s)", title, fmt)
            creation_id = publish_item(user_id, access_token, GRAPH_API_BASE, fmt, image_urls, full_caption)

            logger.info("[%s] 미디어 처리 완료 대기 중...", title)
            _wait_for_container(creation_id, access_token, GRAPH_API_BASE, timeout=300)

            logger.info("[%s] 게시 중...", title)
            post_id = publish_media(user_id, access_token, GRAPH_API_BASE, creation_id)

            permalink = get_permalink(post_id, access_token, GRAPH_API_BASE)
            uploaded_at = datetime.now(tz=timezone.utc).isoformat()

            # ── 7. Notion 상태 업데이트 → Published ──────────────────────
            update_notion_page(page_id, notion_token, {
                "상태": {"select": {"name": "Published"}},
                "게시 URL": {"url": permalink},
                "게시 ID": {"rich_text": [{"type": "text", "text": {"content": post_id}}]},
                "게시 일시": {"date": {"start": uploaded_at}},
                "오류 내용": {"rich_text": []},
            })

            logger.info("[%s] 게시 완료: %s", title, permalink)
            append_log({
                "notion_page_id": page_id,
                "title": title,
                "status": "published",
                "post_id": post_id,
                "post_url": permalink,
                "format": fmt,
                "timestamp": uploaded_at,
            })
            published_count += 1

        except Exception as exc:
            logger.error("[%s] 게시 실패: %s", title, exc)
            error_msg = str(exc)[:2000]
            update_notion_page(page_id, notion_token, {
                "상태": {"select": {"name": "Failed"}},
                "오류 내용": {"rich_text": [{"type": "text", "text": {"content": error_msg}}]},
            })
            append_log({
                "notion_page_id": page_id,
                "title": title,
                "status": "failed",
                "error": error_msg,
                "format": fmt,
                "timestamp": now.isoformat(),
            })

    logger.info("완료: %d개 게시됨 / %d개 조회됨", published_count, len(pages))


if __name__ == "__main__":
    run()
