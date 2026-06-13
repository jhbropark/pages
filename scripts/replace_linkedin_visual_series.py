#!/usr/bin/env python3
"""Replace the current six bilingual LinkedIn posts with diverse visuals."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parent.parent
QUEUE = ROOT / "linkedin" / "queue.json"
RAW = "https://raw.githubusercontent.com/jhbropark/pages/main"
SLUGS = ["insight", "moa-craft", "industry-solution", "methodology", "portfolio", "philosophy"]


def find_current(items: list[dict], slug: str, language: str) -> dict:
    candidates = [
        item
        for item in items
        if item.get("content_type") == slug
        and item.get("language") == language
        and item.get("status") == "uploaded"
    ]
    if not candidates:
        raise RuntimeError(f"No uploaded post found for {slug}/{language}")
    return max(candidates, key=lambda item: item.get("uploaded_at", ""))


def main() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    items = queue["items"]
    now = datetime.now(tz=timezone.utc).isoformat()
    for index, slug in enumerate(SLUGS, 1):
        pair_id = f"linkedin_20260613_diverse_visual_v2_{index:02d}_{slug}"
        for order, language in enumerate(("ko", "en"), 1):
            old = find_current(items, slug, language)
            old["status"] = "delete_pending"
            old["replacement_reason"] = "Replace repeated card template with a distinct visual direction"
            new = {
                key: value
                for key, value in old.items()
                if key not in {
                    "post_urn",
                    "image_urn",
                    "uploaded_at",
                    "deleted_at",
                    "replacement_reason",
                }
            }
            new.update(
                {
                    "id": f"{pair_id}_{language}",
                    "pair_id": pair_id,
                    "pair_order": order,
                    "status": "pending",
                    "image_url": (
                        f"{RAW}/images/linkedin/diverse-series-v2/"
                        f"{index:02d}-{slug}-{language}.jpg"
                    ),
                    "scheduled_time": now,
                    "created_at": now,
                    "generated_by": "codex-diverse-visual-series-v2",
                    "alt_text": f"bbbb.beauty {slug} visual direction, {language}",
                }
            )
            items.append(new)
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Queued 12 replacement posts.")


if __name__ == "__main__":
    main()
