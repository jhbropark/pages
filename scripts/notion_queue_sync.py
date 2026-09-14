#!/usr/bin/env python3
"""
notion_queue_sync.py — Notion "Content Queue" DB → queue/queue.json 브리지 (1/2).

문제: Notion Content Queue에서 상태를 "Approved"로 바꿔도 실제 게시 스크립트
(scripts/instagram_upload.py)는 queue/queue.json만 읽기 때문에 아무 일도
일어나지 않았다. 이 스크립트는 그 간극을 메운다.

동작:
  1. Notion "Content Queue" 데이터소스에서 게시 채널=Instagram, 상태=Approved
     행을 조회한다.
  2. 이미 queue.json에 들어간 적 없는 행(notion_page_id 기준)만 골라
     instagram_upload.py가 읽는 스키마로 변환해 queue.json에 append한다.
  3. 새로 추가한 항목은 Notion 쪽 상태를 "Scheduled"로 바꿔, 다음 동기화 때
     중복으로 집히지 않게 한다 (실제 게시 완료 표시는 notion_writeback.py가
     담당— 게시 전/후 책임을 분리했다).

필요한 환경 변수:
  NOTION_API_KEY            Notion Integration Token (Content Queue DB에 공유되어 있어야 함)
  NOTION_CONTENT_QUEUE_DB_ID  Content Queue 데이터베이스 ID
                              (기본값: 6cc8e695-7db2-4941-86d3-e7c0d9a63b4b)

주의:
  - Content Queue DB의 "이미지 URL" 필드는 텍스트 하나뿐이다. carousel 포맷은
    이 필드에 줄바꿈 또는 쉼표로 구분된 여러 URL이 들어있다고 가정한다.
  - reel/story 포맷은 이 DB에 video_url 컬럼이 없어 아직 지원하지 않는다 —
    발견 시 건너뛰고 경고만 남긴다 (수동 처리 필요).
"""
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).parent.parent
QUEUE_FILE = REPO_ROOT / "queue" / "queue.json"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_DB_ID = "6cc8e695-7db2-4941-86d3-e7c0d9a63b4b"
DEFAULT_SCHEDULE_TIME = "09:00:00+09:00"  # 게시 예정일만 있고 시각이 없을 때 사용

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def query_approved_instagram_rows(token: str, db_id: str) -> list[dict]:
    """상태=Approved, 게시 채널=Instagram 인 Content Queue 행을 모두 가져온다."""
    url = f"{NOTION_API_BASE}/databases/{db_id}/query"
    payload = {
        "filter": {
            "and": [
                {"property": "상태", "select": {"equals": "Approved"}},
                {"property": "게시 채널", "select": {"equals": "Instagram"}},
            ]
        }
    }
    rows, cursor = [], None
    while True:
        body = dict(payload)
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(url, headers=_headers(token), json=body, timeout=30)
        if not r.ok:
            raise RuntimeError(f"Notion 조회 오류 {r.status_code}: {r.text}")
        data = r.json()
        rows.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return rows


def _plain_text(prop: dict) -> str:
    if not prop:
        return ""
    kind = prop.get("type")
    if kind == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if kind == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if kind == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    if kind == "url":
        return prop.get("url") or ""
    if kind == "date":
        d = prop.get("date")
        return (d or {}).get("start") or ""
    return ""


def _split_urls(raw: str) -> list[str]:
    parts = re.split(r"[,\n]+", raw)
    return [p.strip() for p in parts if p.strip()]


def _split_hashtags(raw: str) -> list[str]:
    return [h for h in raw.split() if h.strip()]


def _resolve_scheduled_time(props: dict) -> str:
    dt = _plain_text(props.get("게시 일시", {}))
    if dt:
        return dt
    date_only = _plain_text(props.get("게시 예정일", {}))
    if date_only:
        return f"{date_only}T{DEFAULT_SCHEDULE_TIME}"
    # 예정일조차 없으면 지금 바로 큐에 태운다 (다음 시간당 실행에서 바로 집힘)
    return datetime.now().astimezone().isoformat()


def notion_row_to_queue_item(row: dict) -> dict | None:
    props = row["properties"]
    page_id = row["id"]
    title = _plain_text(props.get("제목", {})) or "(제목 없음)"
    fmt = _plain_text(props.get("포맷", {})) or "single_image"
    caption = _plain_text(props.get("본문", {}))
    hashtags = _split_hashtags(_plain_text(props.get("해시태그", {})))
    image_raw = _plain_text(props.get("이미지 URL", {}))

    if fmt in {"reel", "story"}:
        logger.warning(
            "[%s] 포맷 '%s'는 아직 미지원 (video_url 컬럼 없음) — 건너뜀, 수동 처리 필요",
            title, fmt,
        )
        return None

    if not caption:
        logger.warning("[%s] 본문(캡션)이 비어 있음 — 건너뜀", title)
        return None
    if not image_raw:
        logger.warning("[%s] 이미지 URL이 비어 있음 — 건너뜀 (Krea 생성 대기 중?)", title)
        return None

    item = {
        "id": f"notion-{page_id.replace('-', '')[:12]}",
        "status": "pending",
        "topic": title,
        "caption": caption,
        "hashtags": hashtags,
        "scheduled_time": _resolve_scheduled_time(props),
        "created_at": datetime.now().astimezone().isoformat(),
        "generated_by": "notion_queue_sync",
        "notion_page_id": page_id,
    }

    if fmt == "carousel":
        urls = _split_urls(image_raw)
        if len(urls) < 2:
            logger.warning("[%s] carousel인데 이미지 URL이 %d개뿐 — 건너뜀", title, len(urls))
            return None
        item["image_urls"] = urls
    else:
        item["image_url"] = image_raw

    return item


def update_notion_status(token: str, page_id: str, status: str) -> None:
    url = f"{NOTION_API_BASE}/pages/{page_id}"
    body = {"properties": {"상태": {"select": {"name": status}}}}
    r = requests.patch(url, headers=_headers(token), json=body, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Notion 상태 업데이트 오류 {r.status_code}: {r.text}")


def load_queue() -> dict:
    if not QUEUE_FILE.exists():
        return {"items": []}
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: dict) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def run() -> None:
    token = os.environ.get("NOTION_API_KEY", "").strip()
    db_id = os.environ.get("NOTION_CONTENT_QUEUE_DB_ID", DEFAULT_DB_ID).strip()
    if not token:
        logger.error("NOTION_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    queue = load_queue()
    already_synced = {
        item.get("notion_page_id") for item in queue["items"] if item.get("notion_page_id")
    }

    rows = query_approved_instagram_rows(token, db_id)
    logger.info("Notion에서 Approved/Instagram 행 %d개 조회됨", len(rows))

    added = 0
    for row in rows:
        page_id = row["id"]
        if page_id in already_synced:
            continue
        item = notion_row_to_queue_item(row)
        if item is None:
            continue
        queue["items"].append(item)
        update_notion_status(token, page_id, "Scheduled")
        added += 1
        logger.info("[%s] queue.json에 추가하고 Notion 상태를 Scheduled로 변경함", item["topic"])

    if added:
        save_queue(queue)
    logger.info("동기화 완료: %d건 추가", added)


if __name__ == "__main__":
    run()
