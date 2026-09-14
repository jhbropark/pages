#!/usr/bin/env python3
"""
notion_queue_writeback.py — queue/queue.json → Notion "Content Queue" 결과 반영 (2/2).

notion_queue_sync.py가 Approved 항목을 queue.json으로 옮기고 Notion 상태를
"Scheduled"로 바꿔두면, scripts/instagram_upload.py가 실제 게시를 수행한다.
이 스크립트는 그 게시 결과(성공/실패)를 다시 Notion에 기록해 작업 절차의
6~7단계("게시 완료 후 게시 일시/URL/ID 기록, 상태를 Published로 변경")를
완성한다.

notion_page_id가 있는 queue.json 항목 중 status가 uploaded/failed이고
아직 Notion에 반영하지 않은 것(synced_to_notion 플래그 없음)만 처리한다.

필요한 환경 변수: NOTION_API_KEY, (선택) NOTION_CONTENT_QUEUE_DB_ID
"""
import json
import logging
import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).parent.parent
QUEUE_FILE = REPO_ROOT / "queue" / "queue.json"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

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


def update_published(token: str, page_id: str, post_id: str, post_url: str, uploaded_at: str) -> None:
    url = f"{NOTION_API_BASE}/pages/{page_id}"
    body = {
        "properties": {
            "상태": {"select": {"name": "Published"}},
            "게시 ID": {"rich_text": [{"text": {"content": post_id}}]},
            "게시 URL": {"url": post_url or None},
            "게시 일시": {"date": {"start": uploaded_at}},
        }
    }
    r = requests.patch(url, headers=_headers(token), json=body, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Notion 업데이트 오류 {r.status_code}: {r.text}")


def update_failed(token: str, page_id: str, error: str) -> None:
    url = f"{NOTION_API_BASE}/pages/{page_id}"
    body = {
        "properties": {
            "상태": {"select": {"name": "Failed"}},
            "오류 내용": {"rich_text": [{"text": {"content": error[:2000]}}]},
        }
    }
    r = requests.patch(url, headers=_headers(token), json=body, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Notion 업데이트 오류 {r.status_code}: {r.text}")


def load_queue() -> dict:
    if not QUEUE_FILE.exists():
        return {"items": []}
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: dict) -> None:
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def run() -> None:
    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        logger.error("NOTION_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    queue = load_queue()
    changed = 0
    for item in queue["items"]:
        page_id = item.get("notion_page_id")
        if not page_id or item.get("synced_to_notion"):
            continue
        status = item.get("status")
        try:
            if status == "uploaded":
                update_published(
                    token,
                    page_id,
                    item.get("post_id", ""),
                    item.get("post_url", ""),
                    item.get("uploaded_at", ""),
                )
                item["synced_to_notion"] = True
                changed += 1
                logger.info("[%s] Notion 상태를 Published로 반영함", item.get("topic", item["id"]))
            elif status in {"failed", "invalid"}:
                update_failed(token, page_id, item.get("error") or "; ".join(item.get("errors", [])))
                item["synced_to_notion"] = True
                changed += 1
                logger.info("[%s] Notion 상태를 Failed로 반영함", item.get("topic", item["id"]))
        except Exception as exc:
            logger.error("[%s] Notion 반영 실패: %s", item.get("topic", item["id"]), exc)

    if changed:
        save_queue(queue)
    logger.info("반영 완료: %d건", changed)


if __name__ == "__main__":
    run()
