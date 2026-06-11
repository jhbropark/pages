#!/usr/bin/env python3
"""Replace the four LinkedIn language pairs with full-bleed landscape cards."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "linkedin" / "queue.json"
ENGLISH_SOURCE = ROOT / "content" / "linkedin" / "20260612-visual-style-en.json"
TARGET_PREFIX = "linkedin_20260612_style_"
KST = timezone(timedelta(hours=9))


def without_language_label(text: str) -> str:
    prefix = "English version"
    stripped = text.lstrip()
    if stripped.startswith(prefix):
        stripped = stripped[len(prefix):].lstrip()
    return stripped


def run() -> None:
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    english_source = json.loads(ENGLISH_SOURCE.read_text(encoding="utf-8"))
    for source_item in english_source["items"]:
        source_item["commentary"] = without_language_label(
            source_item["commentary"]
        )
    ENGLISH_SOURCE.write_text(
        json.dumps(english_source, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    source_by_pair = {
        item["pair_id"]: item for item in english_source["items"]
    }
    existing = {item["id"]: item for item in queue["items"]}
    scheduled = datetime.now(tz=KST).replace(microsecond=0).isoformat()
    replacements = []

    for number in range(1, 5):
        pair_id = f"{TARGET_PREFIX}{number:02}"
        korean = existing[pair_id]
        english = existing[f"{pair_id}_en"]
        source = source_by_pair[pair_id]

        for old in (korean, english):
            old["status"] = "delete_pending"
            old["replacement_reason"] = (
                "LinkedIn 1200x627 full-bleed image and English label removal"
            )

        new_pair_id = f"{pair_id}_landscape"
        common = {
            "pair_id": new_pair_id,
            "status": "pending",
            "pillar_id": korean.get("pillar_id"),
            "dm_keyword": source["dm_keyword"],
            "scheduled_time": scheduled,
            "created_at": scheduled,
            "generated_by": "codex-linkedin-landscape-replacement",
        }
        replacements.extend(
            [
                {
                    **common,
                    "id": f"{new_pair_id}_ko",
                    "language": "ko",
                    "pair_order": 1,
                    "topic": korean["topic"],
                    "commentary": korean["commentary"],
                    "hashtags": korean["hashtags"],
                    "image_url": (
                        "https://jhbropark.github.io/pages/images/linkedin/"
                        f"post_20260612_style_{number:02}_ko_landscape.jpg"
                    ),
                    "alt_text": korean["alt_text"],
                },
                {
                    **common,
                    "id": f"{new_pair_id}_en",
                    "language": "en",
                    "pair_order": 2,
                    "topic": source["topic"],
                    "commentary": source["commentary"],
                    "hashtags": source["hashtags"],
                    "image_url": (
                        "https://jhbropark.github.io/pages/images/linkedin/"
                        f"post_20260612_style_{number:02}_en_landscape.jpg"
                    ),
                    "alt_text": source["alt_text"],
                },
            ]
        )

    replacement_ids = {item["id"] for item in replacements}
    queue["items"].extend(
        item for item in replacements if item["id"] not in existing
    )
    QUEUE_FILE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "삭제 대상 8개, 가로형 대체 게시물 "
        f"{len(replacement_ids)}개를 준비했습니다."
    )


if __name__ == "__main__":
    run()
