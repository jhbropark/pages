#!/usr/bin/env python3
"""Queue the reviewed hook-led single image and carousel test posts."""

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parent.parent
QUEUE = ROOT / "queue" / "queue.json"
BASE = "https://jhbropark.github.io/pages/images/tests/data-trust"
NOW = datetime.now(timezone.utc).isoformat()

ITEMS = [
    {
        "id": "post_20260612_hook_single_test",
        "status": "pending",
        "topic": "임상 데이터가 많을수록 고객은 더 신뢰할까",
        "pillar_id": "science_communication",
        "format": "single_image",
        "image_url": f"{BASE}/single-data-trust.jpg",
        "caption": (
            "임상 데이터가 많다고 이해가 깊어지는 것은 아닙니다.\n\n"
            "고객은 숫자보다 먼저 변화와 작동 원리를 봅니다.\n\n"
            "A 그래프, B 경험. 무엇이 더 설득력 있나요?\n"
            "DM 'MOA'로 현재 기술의 시각화 과제를 보내주세요."
        ),
        "hashtags": [
            "#과학커뮤니케이션",
            "#바이오마케팅",
            "#메디컬애니메이션",
            "#더마코스메틱",
            "#bbbbbeauty",
        ],
        "scheduled_time": NOW,
        "created_at": NOW,
        "generated_by": "codex-hook-test",
    },
    {
        "id": "post_20260612_hook_carousel_test",
        "status": "pending",
        "topic": "임상 데이터를 고객의 이해로 번역하는 방법",
        "pillar_id": "science_communication",
        "format": "carousel",
        "image_urls": [
            f"{BASE}/carousel-{index:02d}.jpg" for index in range(1, 7)
        ],
        "caption": (
            "읽히지 않는 근거는 설득이 아닙니다.\n\n"
            "변화, 기전, 근거의 순서로 데이터를 경험으로 바꿔야 합니다.\n\n"
            "A 더 많은 그래프, B 더 빠른 이해. 댓글로 선택해 주세요.\n"
            "DM 'MOA'로 시각화 진단 질문을 받아보세요."
        ),
        "hashtags": [
            "#과학커뮤니케이션",
            "#3DMOA",
            "#바이오마케팅",
            "#브랜드전략",
            "#bbbbbeauty",
        ],
        "scheduled_time": NOW,
        "created_at": NOW,
        "generated_by": "codex-hook-carousel-test",
    },
]


def main():
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    existing = {item["id"] for item in queue["items"]}
    additions = [item for item in ITEMS if item["id"] not in existing]
    queue["items"].extend(additions)
    QUEUE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Queued {len(additions)} test post(s).")


if __name__ == "__main__":
    main()
