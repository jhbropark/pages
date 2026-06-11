#!/usr/bin/env python3
"""Attach English counterparts to existing Korean LinkedIn queue items."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "linkedin" / "queue.json"


def queue_series(source: Path, scheduled_time: str | None = None) -> int:
    series = json.loads(source.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    items = queue.setdefault("items", [])
    by_id = {item.get("id"): item for item in items}
    added = 0

    for entry in series["items"]:
        korean = by_id.get(entry["korean_id"])
        if korean is None:
            raise ValueError(f"한국어 대응 게시물이 없습니다: {entry['korean_id']}")

        korean["pair_id"] = entry["pair_id"]
        korean["language"] = "ko"
        korean["pair_order"] = 1
        korean["dm_keyword"] = entry["dm_keyword"]

        if entry["english_id"] in by_id:
            continue

        english = {
            "id": entry["english_id"],
            "pair_id": entry["pair_id"],
            "language": "en",
            "pair_order": 2,
            "status": "pending",
            "topic": entry["topic"],
            "pillar_id": entry["pillar_id"],
            "dm_keyword": entry["dm_keyword"],
            "commentary": entry["commentary"],
            "hashtags": entry["hashtags"],
            "image_url": entry["image_url"],
            "alt_text": entry["alt_text"],
            "scheduled_time": scheduled_time
            or datetime.now(tz=timezone.utc).isoformat(),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "generated_by": "codex-linkedin-bilingual-series",
        }
        items.append(english)
        by_id[entry["english_id"]] = english
        added += 1

    QUEUE_FILE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--scheduled-time")
    args = parser.parse_args()
    added = queue_series(args.source, args.scheduled_time)
    print(f"LinkedIn 영어 대응 게시물 {added}개를 추가했습니다.")


if __name__ == "__main__":
    main()
