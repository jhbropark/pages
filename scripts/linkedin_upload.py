#!/usr/bin/env python3
"""Publish due LinkedIn image posts using LinkedIn's versioned REST APIs."""

import json
import logging
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
QUEUE_FILE = REPO_ROOT / "linkedin" / "queue.json"
LOG_FILE = REPO_ROOT / "logs" / "linkedin_upload_log.json"

API_BASE = "https://api.linkedin.com/rest"
API_VERSION = os.environ.get("LINKEDIN_API_VERSION", "202605").strip()
MAX_COMMENTARY_LENGTH = 3000
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _headers(access_token: str, *, json_content: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Linkedin-Version": API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if json_content:
        headers["Content-Type"] = "application/json"
    return headers


def _request_json(
    method: str,
    url: str,
    access_token: str,
    payload: dict | None = None,
) -> tuple[dict, dict]:
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=_headers(access_token, json_content=payload is not None),
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read()
            parsed = json.loads(body) if body else {}
            return parsed, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LinkedIn API 오류 {exc.code}: {body}") from exc


def _download_image(image_url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(
        image_url,
        headers={"User-Agent": "bbbb.beauty-linkedin-publisher/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content = response.read()
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"이미지 다운로드 오류 {exc.code}: {image_url}") from exc
    if not content:
        raise RuntimeError("다운로드한 이미지가 비어 있습니다.")
    return content, content_type


def initialize_image_upload(access_token: str, author_urn: str) -> tuple[str, str]:
    result, _ = _request_json(
        "POST",
        f"{API_BASE}/images?action=initializeUpload",
        access_token,
        {"initializeUploadRequest": {"owner": author_urn}},
    )
    value = result.get("value", {})
    upload_url = value.get("uploadUrl")
    image_urn = value.get("image")
    if not upload_url or not image_urn:
        raise RuntimeError(f"이미지 업로드 초기화 응답이 올바르지 않습니다: {result}")
    return upload_url, image_urn


def upload_image(upload_url: str, image_data: bytes, content_type: str) -> None:
    request = urllib.request.Request(
        upload_url,
        data=image_data,
        method="PUT",
        headers={"Content-Type": content_type or "application/octet-stream"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status not in {200, 201}:
                raise RuntimeError(f"이미지 바이너리 업로드 실패: HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"이미지 바이너리 업로드 오류 {exc.code}: {body}") from exc


def create_post(
    access_token: str,
    author_urn: str,
    commentary: str,
    image_urn: str,
    alt_text: str,
) -> str:
    payload = {
        "author": author_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {
                "altText": alt_text[:4086],
                "id": image_urn,
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    _, headers = _request_json(
        "POST",
        f"{API_BASE}/posts",
        access_token,
        payload,
    )
    post_urn = headers.get("x-restli-id") or headers.get("X-RestLi-Id")
    if not post_urn:
        raise RuntimeError("게시 성공 응답에 x-restli-id가 없습니다.")
    return post_urn


def validate_item(item: dict) -> list[str]:
    errors = []
    commentary = item.get("commentary", "")
    image_url = item.get("image_url", "")
    if not commentary:
        errors.append("commentary가 없습니다.")
    elif len(commentary) > MAX_COMMENTARY_LENGTH:
        errors.append(
            f"commentary가 너무 깁니다: {len(commentary)}자 "
            f"(최대 {MAX_COMMENTARY_LENGTH}자)"
        )
    if not image_url:
        errors.append("image_url이 없습니다.")
    else:
        extension = Path(urllib.parse.urlparse(image_url).path).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            errors.append(f"지원하지 않는 이미지 형식: {extension}")
    if not item.get("scheduled_time"):
        errors.append("scheduled_time이 없습니다.")
    return errors


def is_due(value: str, now: datetime) -> bool:
    scheduled = datetime.fromisoformat(value)
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    return scheduled <= now


def load_queue() -> dict:
    with open(QUEUE_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def save_queue(queue: dict) -> None:
    with open(QUEUE_FILE, "w", encoding="utf-8") as handle:
        json.dump(queue, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def append_log(entry: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logs = []
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as handle:
            logs = json.load(handle)
    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as handle:
        json.dump(logs, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def build_commentary(item: dict) -> str:
    hashtags = " ".join(item.get("hashtags", []))
    commentary = item["commentary"].strip()
    return f"{commentary}\n\n{hashtags}" if hashtags else commentary


def run() -> None:
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author_urn = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip()
    if not access_token or not author_urn:
        logger.error(
            "LINKEDIN_ACCESS_TOKEN과 LINKEDIN_AUTHOR_URN을 모두 설정해야 합니다."
        )
        sys.exit(1)
    if not (
        author_urn.startswith("urn:li:person:")
        or author_urn.startswith("urn:li:organization:")
    ):
        logger.error(
            "LINKEDIN_AUTHOR_URN은 urn:li:person:... 또는 "
            "urn:li:organization:... 형식이어야 합니다."
        )
        sys.exit(1)

    queue = load_queue()
    now = datetime.now(tz=timezone.utc)
    pending = [item for item in queue.get("items", []) if item.get("status") == "pending"]
    logger.info("LinkedIn 업로드 대기 항목: %d개", len(pending))

    uploaded_count = 0
    for item in pending:
        item_id = item.get("id", "unknown")
        scheduled_time = item.get("scheduled_time", "")
        if not scheduled_time or not is_due(scheduled_time, now):
            logger.info("[%s] 아직 예약 시간이 아닙니다: %s", item_id, scheduled_time)
            continue

        errors = validate_item(item)
        if errors:
            item["status"] = "invalid"
            item["errors"] = errors
            append_log(
                {
                    "id": item_id,
                    "status": "invalid",
                    "errors": errors,
                    "timestamp": now.isoformat(),
                }
            )
            continue

        try:
            commentary = build_commentary(item)
            if len(commentary) > MAX_COMMENTARY_LENGTH:
                raise RuntimeError(
                    f"해시태그 포함 본문이 {MAX_COMMENTARY_LENGTH}자를 초과합니다."
                )
            logger.info("[%s] 이미지 다운로드 중...", item_id)
            image_data, content_type = _download_image(item["image_url"])
            if not content_type.startswith("image/"):
                guessed_type, _ = mimetypes.guess_type(item["image_url"])
                content_type = guessed_type or "application/octet-stream"

            logger.info("[%s] LinkedIn 이미지 업로드 초기화 중...", item_id)
            upload_url, image_urn = initialize_image_upload(access_token, author_urn)
            upload_image(upload_url, image_data, content_type)

            logger.info("[%s] LinkedIn 게시 중...", item_id)
            post_urn = create_post(
                access_token,
                author_urn,
                commentary,
                image_urn,
                item.get("alt_text", "bbbb.beauty 과학 커뮤니케이션 콘텐츠"),
            )
            uploaded_at = datetime.now(tz=timezone.utc).isoformat()
            item["status"] = "uploaded"
            item["post_urn"] = post_urn
            item["image_urn"] = image_urn
            item["uploaded_at"] = uploaded_at
            append_log(
                {
                    "id": item_id,
                    "status": "uploaded",
                    "post_urn": post_urn,
                    "timestamp": uploaded_at,
                }
            )
            logger.info("[%s] 업로드 완료: %s", item_id, post_urn)
            uploaded_count += 1
        except Exception as exc:
            logger.error("[%s] 업로드 실패: %s", item_id, exc)
            item["status"] = "failed"
            item["error"] = str(exc)
            append_log(
                {
                    "id": item_id,
                    "status": "failed",
                    "error": str(exc),
                    "timestamp": now.isoformat(),
                }
            )

    save_queue(queue)
    logger.info("완료: %d개 LinkedIn 게시됨", uploaded_count)


if __name__ == "__main__":
    run()
