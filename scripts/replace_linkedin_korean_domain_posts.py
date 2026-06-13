#!/usr/bin/env python3
"""Replace Korean LinkedIn posts whose brand name became an IDN link."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from linkedin_upload import sanitize_linkedin_text


ROOT = Path(__file__).parent.parent
QUEUE = ROOT / "linkedin" / "queue.json"
PREFIX = "linkedin_20260613_six_types_"


def main() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    items = queue["items"]
    existing_ids = {item["id"] for item in items}
    now = datetime.now(tz=timezone.utc).isoformat()
    replacements = []

    for item in items:
        if not (
            item["id"].startswith(PREFIX)
            and item.get("language") == "ko"
            and item.get("status") == "uploaded"
        ):
            continue

        replacement_id = f"{item['id']}_domain_fixed"
        item["status"] = "delete_pending"
        if replacement_id in existing_ids:
            continue

        replacement = deepcopy(item)
        replacement.update(
            {
                "id": replacement_id,
                "pair_id": f"{item['pair_id']}_domain_fixed",
                "status": "pending",
                "commentary": sanitize_linkedin_text(item["commentary"]),
                "scheduled_time": now,
                "created_at": now,
                "generated_by": "codex-linkedin-domain-fix",
            }
        )
        for field in (
            "post_urn",
            "image_urn",
            "uploaded_at",
            "deleted_at",
            "error",
            "errors",
        ):
            replacement.pop(field, None)
        replacements.append(replacement)
        existing_ids.add(replacement_id)

    items.extend(replacements)
    QUEUE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"교체 대상 {len(replacements)}개를 추가했습니다.")


if __name__ == "__main__":
    main()
