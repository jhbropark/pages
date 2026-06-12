#!/usr/bin/env python3
"""
Instagram 예약 업로드 스크립트
Meta Graph API를 사용하여 예약된 콘텐츠를 Instagram에 자동 게시합니다.

필요한 환경 변수:
  INSTAGRAM_USER_ID      - Instagram 비즈니스 계정 ID
  INSTAGRAM_ACCESS_TOKEN - Meta Graph API 장기 액세스 토큰
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

# --- 경로 설정 ---
REPO_ROOT = Path(__file__).parent.parent
QUEUE_FILE = REPO_ROOT / "queue" / "queue.json"
LOG_FILE = REPO_ROOT / "logs" / "upload_log.json"

# --- 유효성 검사 상수 ---
MAX_CAPTION_LENGTH = 2200
MAX_HASHTAG_COUNT = 30
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
GRAPH_API_VERSION = os.environ.get("INSTAGRAM_GRAPH_API_VERSION", "v25.0")
PUBLISHING_POLL_INTERVAL = 60

# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# 토큰 종류에 따라 API 호스트가 다릅니다.
# - "Instagram 로그인이 포함된 API" 토큰(IGAA...)  → graph.instagram.com
# - Facebook 로그인 기반 토큰(EAA...)              → graph.facebook.com
def _resolve_api_base(token: str) -> str:
    if token.isdigit():
        raise ValueError(
            "INSTAGRAM_ACCESS_TOKEN에 숫자 Instagram 계정 ID가 저장되어 있습니다. "
            "액세스 토큰 전체 문자열을 저장하고, 숫자 ID는 INSTAGRAM_USER_ID에 저장하세요."
        )
    if len(token) < 40:
        raise ValueError(
            "INSTAGRAM_ACCESS_TOKEN 값이 액세스 토큰 형식보다 너무 짧습니다."
        )
    if token.startswith("IG"):
        return f"https://graph.instagram.com/{GRAPH_API_VERSION}"
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}"


GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


# ---------------------------------------------------------------------------
# 유효성 검사
# ---------------------------------------------------------------------------

def validate_item(item: dict) -> list[str]:
    """콘텐츠 항목을 검증하고 오류 목록을 반환합니다."""
    errors = []
    content_format = item.get("format", "single_image")

    if content_format == "reel":
        video_url = item.get("video_url", "")
        if not video_url:
            errors.append("릴스 video_url이 없습니다.")
        else:
            ext = Path(urllib.parse.urlparse(video_url).path).suffix.lower()
            if ext not in ALLOWED_VIDEO_EXTENSIONS:
                errors.append(
                    f"지원하지 않는 릴스 형식: {ext} "
                    f"(허용: {ALLOWED_VIDEO_EXTENSIONS})"
                )
    elif content_format == "story":
        image_url = item.get("image_url", "")
        video_url = item.get("video_url", "")
        if not image_url and not video_url:
            errors.append("스토리 image_url 또는 video_url이 없습니다.")
        source_url = image_url or video_url
        ext = Path(urllib.parse.urlparse(source_url).path).suffix.lower()
        allowed = ALLOWED_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
        if ext not in allowed:
            errors.append(f"지원하지 않는 스토리 형식: {ext} (허용: {allowed})")
    # 단일 이미지 또는 2~10장 캐러셀 URL 확인
    elif item.get("image_urls") is not None:
        image_urls = item["image_urls"]
        if not isinstance(image_urls, list) or not 2 <= len(image_urls) <= 10:
            errors.append("image_urls는 2~10장의 이미지여야 합니다.")
        else:
            for image_url in image_urls:
                ext = Path(urllib.parse.urlparse(image_url).path).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    errors.append(
                        f"지원하지 않는 캐러셀 이미지 형식: {ext} "
                        f"(허용: {ALLOWED_EXTENSIONS})"
                    )
    else:
        image_url: str = item.get("image_url", "")
        if not image_url:
            errors.append("image_url이 없습니다.")
        else:
            ext = Path(urllib.parse.urlparse(image_url).path).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                errors.append(
                    f"지원하지 않는 이미지 형식: {ext} "
                    f"(허용: {ALLOWED_EXTENSIONS})"
                )

    # 캡션 길이 확인
    caption: str = item.get("caption", "")
    if len(caption) > MAX_CAPTION_LENGTH:
        errors.append(f"캡션이 너무 깁니다: {len(caption)}자 (최대 {MAX_CAPTION_LENGTH}자)")

    # 해시태그 수 확인
    hashtags: list = item.get("hashtags", [])
    if len(hashtags) > MAX_HASHTAG_COUNT:
        errors.append(f"해시태그가 너무 많습니다: {len(hashtags)}개 (최대 {MAX_HASHTAG_COUNT}개)")

    # 예약 시간 확인
    if not item.get("scheduled_time"):
        errors.append("scheduled_time이 없습니다.")

    return errors


def inspect_local_mp4(video_url: str) -> list[str]:
    """저장소에서 제공하는 MP4가 Meta의 컨테이너 요구사항을 만족하는지 검사합니다."""
    parsed = urllib.parse.urlparse(video_url)
    marker = "/pages/"
    if parsed.hostname != "jhbropark.github.io" or marker not in parsed.path:
        return []

    relative_path = urllib.parse.unquote(parsed.path.split(marker, 1)[1])
    local_path = REPO_ROOT / Path(relative_path)
    if not local_path.exists() or local_path.suffix.lower() != ".mp4":
        return []

    payload = local_path.read_bytes()
    errors = []
    moov_offset = payload.find(b"moov")
    mdat_offset = payload.find(b"mdat")
    if moov_offset < 0:
        errors.append("MP4에 moov atom이 없습니다.")
    elif mdat_offset >= 0 and moov_offset > mdat_offset:
        errors.append("MP4 moov atom이 파일 시작 부분에 없습니다.")
    if b"edts" in payload or b"elst" in payload:
        errors.append("Meta가 허용하지 않는 MP4 편집 목록(edts/elst)이 포함되어 있습니다.")
    return errors


# ---------------------------------------------------------------------------
# Meta Graph API 호출
# ---------------------------------------------------------------------------

def _api_post(endpoint: str, params: dict) -> dict:
    """Graph API에 POST 요청을 보내고 JSON 응답을 반환합니다."""
    data = urllib.parse.urlencode(params).encode("utf-8")
    url = f"{GRAPH_API_BASE}/{endpoint}"
    last_error = None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"API 오류 {e.code}: {body}")
            is_transient = '"is_transient":true' in body or '"code":2' in body
            if not is_transient or attempt == 4:
                raise last_error from e
            delay = 5 * (2 ** attempt)
            logger.warning(
                "Meta 일시 오류로 %d초 후 재시도합니다 (%d/5).",
                delay,
                attempt + 2,
            )
            time.sleep(delay)
    raise last_error


def _api_get(endpoint: str, access_token: str, fields: str = "") -> dict:
    """Graph API GET 요청을 보내고 JSON 응답을 반환합니다."""
    params = {"access_token": access_token}
    if fields:
        params["fields"] = fields
    url = f"{GRAPH_API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    last_error = None
    for attempt in range(5):
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"API 조회 오류 {e.code}: {body}")
            is_transient = '"is_transient":true' in body or '"code":2' in body
            if not is_transient or attempt == 4:
                raise last_error from e
            delay = 5 * (2 ** attempt)
            logger.warning(
                "Meta 조회 일시 오류로 %d초 후 재시도합니다 (%d/5).",
                delay,
                attempt + 2,
            )
            time.sleep(delay)
    raise last_error


def _rupload_from_url(upload_uri: str, access_token: str, video_url: str) -> dict:
    """공개 URL의 영상을 Meta 업로드 서버로 직접 전달합니다."""
    last_error = None
    for attempt in range(5):
        req = urllib.request.Request(
            upload_uri,
            data=b"",
            headers={
                "Authorization": f"OAuth {access_token}",
                "file_url": video_url,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                if not result.get("success"):
                    raise RuntimeError(
                        f"Meta 영상 업로드 실패: {json.dumps(result, ensure_ascii=False)}"
                    )
                return result
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Meta 영상 업로드 오류 {exc.code}: {body}")
            is_transient = '"retriable":true' in body or '"is_transient":true' in body
            if not is_transient or attempt == 4:
                raise last_error from exc
            delay = 5 * (2 ** attempt)
            logger.warning(
                "Meta 영상 업로드 일시 오류로 %d초 후 재시도합니다 (%d/5).",
                delay,
                attempt + 2,
            )
            time.sleep(delay)
    raise last_error


def create_resumable_video_container(
    user_id: str,
    access_token: str,
    media_type: str,
    video_url: str,
    caption: str = "",
    share_to_feed: bool = False,
) -> str:
    """영상 컨테이너를 만든 뒤 rupload를 통해 Meta 서버에 영상을 전달합니다."""
    params = {
        "media_type": media_type,
        "upload_type": "resumable",
        "access_token": access_token,
    }
    if caption:
        params["caption"] = caption
    if media_type == "REELS":
        params["share_to_feed"] = "true" if share_to_feed else "false"

    result = _api_post(f"{user_id}/media", params)
    creation_id = result["id"]
    upload_uri = result.get("uri")
    if not upload_uri:
        upload_uri = (
            f"https://rupload.facebook.com/ig-api-upload/"
            f"{GRAPH_API_VERSION}/{creation_id}"
        )
    logger.info("Meta 영상 서버로 업로드 중... (creation_id=%s)", creation_id)
    _rupload_from_url(upload_uri, access_token, video_url)
    return creation_id


def diagnose_access(access_token: str) -> str:
    """토큰 소유 계정을 확인하고 실제 숫자 Instagram 계정 ID를 반환합니다."""
    profile = _api_get(
        "me",
        access_token,
        "id,user_id,username,account_type,media_count",
    )
    resolved_id = str(profile.get("user_id") or profile.get("id") or "").strip()
    if not resolved_id.isdigit():
        raise RuntimeError("토큰에서 숫자 Instagram 계정 ID를 확인하지 못했습니다.")

    logger.info(
        "토큰 계정 확인 완료: username=%s, account_type=%s, user_id=%s",
        profile.get("username", "unknown"),
        profile.get("account_type", "unknown"),
        resolved_id,
    )

    try:
        permissions = _api_get("me/permissions", access_token)
        granted = [
            item.get("permission")
            for item in permissions.get("data", [])
            if item.get("status") == "granted"
        ]
        logger.info("승인된 Instagram 권한: %s", ", ".join(granted) or "확인되지 않음")
    except RuntimeError as exc:
        logger.warning("권한 목록 조회를 지원하지 않거나 실패했습니다: %s", exc)

    try:
        limit = _api_get(
            f"{resolved_id}/content_publishing_limit",
            access_token,
            "config,quota_usage",
        )
        logger.info("콘텐츠 게시 한도 상태: %s", json.dumps(limit, ensure_ascii=False))
    except RuntimeError as exc:
        logger.warning("콘텐츠 게시 한도 조회 실패: %s", exc)

    return resolved_id


def create_media_container(user_id: str, access_token: str, image_url: str, caption: str) -> str:
    """이미지 미디어 컨테이너를 생성하고 creation_id를 반환합니다."""
    result = _api_post(
        f"{user_id}/media",
        {
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
    )
    return result["id"]


def create_carousel_container(
    user_id: str,
    access_token: str,
    image_urls: list[str],
    caption: str,
) -> str:
    """이미지 자식 컨테이너와 캐러셀 부모 컨테이너를 생성합니다."""
    child_ids = []
    for image_url in image_urls:
        result = _api_post(
            f"{user_id}/media",
            {
                "image_url": image_url,
                "is_carousel_item": "true",
                "access_token": access_token,
            },
        )
        child_id = result["id"]
        wait_for_container_ready(child_id, access_token)
        child_ids.append(child_id)

    result = _api_post(
        f"{user_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": access_token,
        },
    )
    return result["id"]


def create_reel_container(
    user_id: str,
    access_token: str,
    video_url: str,
    caption: str,
    cover_url: str = "",
) -> str:
    """릴스 비디오 컨테이너를 생성합니다."""
    if not cover_url:
        return create_resumable_video_container(
            user_id,
            access_token,
            "REELS",
            video_url,
            caption,
            share_to_feed=True,
        )
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": access_token,
    }
    if cover_url:
        params["cover_url"] = cover_url
    try:
        result = _api_post(f"{user_id}/media", params)
    except RuntimeError as exc:
        if cover_url and "cover_url" in str(exc):
            logger.warning("현재 API에서 cover_url을 거부하여 자동 커버로 재시도합니다.")
            params.pop("cover_url", None)
            result = _api_post(f"{user_id}/media", params)
        else:
            raise
    return result["id"]


def create_story_container(
    user_id: str,
    access_token: str,
    image_url: str = "",
    video_url: str = "",
) -> str:
    """이미지 또는 비디오 스토리 컨테이너를 생성합니다."""
    if video_url:
        return create_resumable_video_container(
            user_id,
            access_token,
            "STORIES",
            video_url,
        )
    params = {
        "media_type": "STORIES",
        "access_token": access_token,
    }
    params["image_url"] = image_url
    result = _api_post(f"{user_id}/media", params)
    return result["id"]


def wait_for_container_ready(
    creation_id: str,
    access_token: str,
    timeout: int = 300,
    poll_interval: int = PUBLISHING_POLL_INTERVAL,
) -> None:
    """Meta 권장 주기에 맞춰 미디어 컨테이너의 처리 상태를 확인합니다."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = _api_get(
            creation_id,
            access_token,
            "status_code,status,video_status",
        )
        status_code = result.get("status_code", "")
        status_detail = result.get("status", "")
        if status_code in {"FINISHED", "PUBLISHED"}:
            return
        if status_code in {"ERROR", "EXPIRED"}:
            detail = f": {status_detail}" if status_detail else ""
            raise RuntimeError(
                f"미디어 컨테이너 처리 실패 "
                f"(creation_id={creation_id}, status_code={status_code}{detail})"
            )
        logger.info(
            "미디어 처리 대기 중... "
            "(creation_id=%s, status_code=%s, status=%s, video_status=%s)",
            creation_id,
            status_code or "unknown",
            status_detail or "unknown",
            json.dumps(result.get("video_status", {}), ensure_ascii=False),
        )
        remaining = deadline - time.time()
        if remaining > 0:
            time.sleep(min(poll_interval, remaining))
    raise RuntimeError(f"미디어 컨테이너가 {timeout}초 내에 준비되지 않았습니다.")


def publish_media(user_id: str, access_token: str, creation_id: str) -> str:
    """미디어 컨테이너를 게시하고 게시물 ID를 반환합니다.

    이미지 처리가 끝나기 전에 게시하면 9007(Media ID is not available)이
    발생하므로 짧은 간격으로 몇 차례 재시도합니다.
    """
    last_error: Exception | None = None
    for attempt in range(5):
        if attempt:
            time.sleep(10)
            logger.info("게시 재시도 %d/4...", attempt)
        try:
            result = _api_post(
                f"{user_id}/media_publish",
                {
                    "creation_id": creation_id,
                    "access_token": access_token,
                },
            )
            return result["id"]
        except RuntimeError as exc:
            last_error = exc
            if "9007" not in str(exc) and "not ready" not in str(exc):
                raise
    raise last_error


def get_post_permalink(post_id: str, access_token: str) -> str:
    """게시물 permalink를 가져옵니다."""
    params = urllib.parse.urlencode({"fields": "permalink", "access_token": access_token})
    url = f"{GRAPH_API_BASE}/{post_id}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("permalink", f"https://www.instagram.com/p/{post_id}/")
    except Exception:
        return f"https://www.instagram.com/p/{post_id}/"


# ---------------------------------------------------------------------------
# 큐 및 로그 관리
# ---------------------------------------------------------------------------

def load_queue() -> dict:
    if not QUEUE_FILE.exists():
        logger.warning("queue.json 파일이 없습니다: %s", QUEUE_FILE)
        return {"items": []}
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: dict) -> None:
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def append_log(entry: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logs = []
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = json.load(f)
    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------------------------

def is_due(scheduled_time_str: str, now: datetime) -> bool:
    """예약 시간이 현재 시각 이전인지 확인합니다."""
    dt = datetime.fromisoformat(scheduled_time_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt <= now


def build_full_caption(caption: str, hashtags: list[str]) -> str:
    tag_str = " ".join(hashtags)
    if tag_str:
        return f"{caption}\n\n{tag_str}"
    return caption


def run() -> None:
    # 복사/붙여넣기 시 섞여 들어간 공백·줄바꿈 제거
    user_id = os.environ.get("INSTAGRAM_USER_ID", "").strip()
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()

    if not user_id or not access_token:
        logger.error("환경 변수 INSTAGRAM_USER_ID 또는 INSTAGRAM_ACCESS_TOKEN이 설정되지 않았습니다.")
        sys.exit(1)

    global GRAPH_API_BASE
    GRAPH_API_BASE = _resolve_api_base(access_token)
    logger.info("API 호스트: %s (토큰 접두사: %s...)", GRAPH_API_BASE, access_token[:4])

    resolved_user_id = diagnose_access(access_token)
    if user_id.isdigit() and user_id != resolved_user_id:
        logger.warning(
            "Secret의 계정 ID(%s)가 토큰 계정 ID(%s)와 달라 토큰 계정 ID를 사용합니다.",
            user_id,
            resolved_user_id,
        )
    user_id = resolved_user_id

    queue = load_queue()
    now = datetime.now(tz=timezone.utc)
    pending = [item for item in queue["items"] if item.get("status") == "pending"]

    if not pending:
        logger.info("업로드 대기 중인 콘텐츠가 없습니다.")
        return

    logger.info("대기 중인 항목: %d개", len(pending))
    uploaded_count = 0

    for item in pending:
        item_id = item.get("id", "unknown")

        # 예약 시간 확인
        scheduled = item.get("scheduled_time", "")
        if not scheduled or not is_due(scheduled, now):
            logger.info("[%s] 아직 예약 시간이 아닙니다: %s", item_id, scheduled)
            continue

        # 유효성 검사
        errors = validate_item(item)
        video_url = item.get("video_url", "")
        if video_url:
            errors.extend(inspect_local_mp4(video_url))
        if errors:
            logger.warning("[%s] 유효성 검사 실패: %s", item_id, "; ".join(errors))
            item["status"] = "invalid"
            item["errors"] = errors
            append_log({
                "id": item_id,
                "status": "invalid",
                "errors": errors,
                "timestamp": now.isoformat(),
            })
            continue

        # 업로드
        full_caption = build_full_caption(item.get("caption", ""), item.get("hashtags", []))
        try:
            logger.info("[%s] 미디어 컨테이너 생성 중...", item_id)
            content_format = item.get("format", "single_image")
            if content_format == "reel":
                creation_id = create_reel_container(
                    user_id,
                    access_token,
                    item["video_url"],
                    full_caption,
                    item.get("cover_url", ""),
                )
            elif content_format == "story":
                creation_id = create_story_container(
                    user_id,
                    access_token,
                    item.get("image_url", ""),
                    item.get("video_url", ""),
                )
            elif item.get("image_urls"):
                creation_id = create_carousel_container(
                    user_id,
                    access_token,
                    item["image_urls"],
                    full_caption,
                )
            else:
                creation_id = create_media_container(
                    user_id,
                    access_token,
                    item["image_url"],
                    full_caption,
                )

            item["creation_id"] = creation_id
            item["container_created_at"] = datetime.now(tz=timezone.utc).isoformat()
            save_queue(queue)
            logger.info("[%s] 미디어 처리 완료 대기 중...", item_id)
            wait_timeout = 300
            wait_for_container_ready(creation_id, access_token, timeout=wait_timeout)

            logger.info("[%s] 게시 중...", item_id)
            post_id = publish_media(user_id, access_token, creation_id)

            permalink = get_post_permalink(post_id, access_token)
            uploaded_at = datetime.now(tz=timezone.utc).isoformat()

            item["status"] = "uploaded"
            item["post_id"] = post_id
            item["post_url"] = permalink
            item["uploaded_at"] = uploaded_at

            append_log({
                "id": item_id,
                "status": "uploaded",
                "post_id": post_id,
                "post_url": permalink,
                "timestamp": uploaded_at,
            })

            logger.info("[%s] 업로드 완료: %s", item_id, permalink)
            uploaded_count += 1

        except Exception as exc:
            logger.error("[%s] 업로드 실패: %s", item_id, exc)
            item["status"] = "failed"
            item["error"] = str(exc)
            append_log({
                "id": item_id,
                "status": "failed",
                "error": str(exc),
                "creation_id": item.get("creation_id"),
                "timestamp": now.isoformat(),
            })

    save_queue(queue)
    logger.info("완료: %d개 업로드됨", uploaded_count)


if __name__ == "__main__":
    run()
