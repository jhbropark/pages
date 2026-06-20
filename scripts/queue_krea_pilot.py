#!/usr/bin/env python3
"""
Krea 파일럿 콘텐츠를 발행 큐에 draft 상태로 등록하는 스크립트

content/instagram/20260620-krea-pilot.json 과
content/linkedin/20260620-krea-pilot.json 의 초안을 각각
queue/queue.json, linkedin/queue.json 에 추가한다.

안전장치
- 모든 항목은 status="draft"로 등록한다. 업로더는 status=="pending"인
  항목만 발행하므로(scripts/instagram_upload.py, scripts/linkedin_upload.py),
  Krea 비주얼이 렌더·고증 검수를 통과하기 전에는 발행되지 않는다.
- id 기준 멱등. 이미 있는 id는 건너뛴다.
- 발행 준비가 끝나면 scheduled_time을 채우고 status를 "pending"으로 바꾼다.

사용법
  python scripts/queue_krea_pilot.py --dry-run   # 추가될 항목만 출력
  python scripts/queue_krea_pilot.py             # 큐에 draft로 등록
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IG_CONTENT = ROOT / "content" / "instagram" / "20260620-krea-pilot.json"
LI_CONTENT = ROOT / "content" / "linkedin" / "20260620-krea-pilot.json"
IG_QUEUE = ROOT / "queue" / "queue.json"
LI_QUEUE = ROOT / "linkedin" / "queue.json"

GENERATED_BY = "claude-krea-pilot"


def build_instagram_items(content: dict, now_iso: str) -> list[dict]:
    items = []
    for entry in content["items"]:
        items.append(
            {
                "id": entry["id"],
                "status": "draft",
                "format": entry.get("format", "carousel"),
                "topic": entry["topic"],
                "pillar_id": entry["pillar_id"],
                "dm_keyword": entry["dm_keyword"],
                "image_urls": entry["image_urls"],
                "caption": entry["caption"],
                "hashtags": entry["hashtags"],
                "alt_text": entry.get("alt_text", ""),
                "scheduled_time": None,
                "created_at": now_iso,
                "generated_by": GENERATED_BY,
            }
        )
    return items


def build_linkedin_items(content: dict, now_iso: str) -> list[dict]:
    items = []
    for entry in content["items"]:
        common = {
            "status": "draft",
            "pair_id": entry["pair_id"],
            "topic": entry["topic"],
            "pillar_id": entry["pillar_id"],
            "dm_keyword": entry["dm_keyword"],
            "alt_text": entry.get("alt_text", ""),
            "scheduled_time": None,
            "created_at": now_iso,
            "generated_by": GENERATED_BY,
        }
        items.append(
            {
                **common,
                "id": entry["korean_id"],
                "language": "ko",
                "pair_order": 1,
                "commentary": entry["commentary_ko"],
                "hashtags": entry["hashtags_ko"],
                "image_url": entry["image_url_ko"],
            }
        )
        items.append(
            {
                **common,
                "id": entry["english_id"],
                "language": "en",
                "pair_order": 2,
                "commentary": entry["commentary_en"],
                "hashtags": entry["hashtags_en"],
                "image_url": entry["image_url_en"],
            }
        )
    return items


def merge_into_queue(queue: dict, new_items: list[dict]) -> int:
    """id 기준으로 멱등하게 큐에 추가하고 추가된 개수를 반환합니다."""
    items = queue.setdefault("items", [])
    existing = {item.get("id") for item in items}
    added = 0
    for item in new_items:
        if item["id"] in existing:
            continue
        items.append(item)
        existing.add(item["id"])
        added += 1
    return added


def register(dry_run: bool) -> dict:
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    ig_content = json.loads(IG_CONTENT.read_text(encoding="utf-8"))
    li_content = json.loads(LI_CONTENT.read_text(encoding="utf-8"))
    ig_new = build_instagram_items(ig_content, now_iso)
    li_new = build_linkedin_items(li_content, now_iso)

    ig_queue = json.loads(IG_QUEUE.read_text(encoding="utf-8"))
    li_queue = json.loads(LI_QUEUE.read_text(encoding="utf-8"))
    ig_added = merge_into_queue(ig_queue, ig_new)
    li_added = merge_into_queue(li_queue, li_new)

    if not dry_run:
        IG_QUEUE.write_text(
            json.dumps(ig_queue, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        LI_QUEUE.write_text(
            json.dumps(li_queue, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return {
        "instagram_added": ig_added,
        "linkedin_added": li_added,
        "instagram_ids": [i["id"] for i in ig_new],
        "linkedin_ids": [i["id"] for i in li_new],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Krea 파일럿을 큐에 draft로 등록")
    parser.add_argument(
        "--dry-run", action="store_true", help="큐를 수정하지 않고 추가될 항목만 출력"
    )
    args = parser.parse_args()

    result = register(args.dry_run)
    verb = "추가 예정" if args.dry_run else "추가"
    print(f"Instagram {result['instagram_added']}개 {verb} (draft)")
    print(f"LinkedIn {result['linkedin_added']}개 {verb} (draft)")
    if args.dry_run:
        for cid in result["instagram_ids"]:
            print(f"  IG  {cid}")
        for cid in result["linkedin_ids"]:
            print(f"  LI  {cid}")
    else:
        print("발행 준비가 끝나면 scheduled_time을 채우고 status를 pending으로 바꾸세요.")


if __name__ == "__main__":
    main()
