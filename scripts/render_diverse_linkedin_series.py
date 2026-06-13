#!/usr/bin/env python3
"""Render six bilingual LinkedIn image concepts and a review sheet."""

from pathlib import Path

from visual_direction_renderer import create_contact_sheet, render_direction


ROOT = Path(__file__).parent.parent
OUT = ROOT / "images" / "linkedin" / "diverse-series-v2"
SERIES = [
    ("insight", "정보보다 먼저 이해의 순서를 설계합니다.", "Design the sequence before adding information."),
    ("moa-craft", "모든 움직임에는 과학적 근거가 필요합니다.", "Every movement needs scientific logic."),
    ("industry-solution", "그래프가 읽히지 않는다면 경험의 순서를 바꿔야 합니다.", "When graphs are ignored, redesign the experience."),
    ("methodology", "좋은 장면은 검수 이전에 설계됩니다.", "Strong scenes are designed before final review."),
    ("portfolio", "하나의 기술을 채널마다 다르게 경험시킵니다.", "One technology. Different channel experiences."),
    ("philosophy", "기술은 정확하게, 메시지는 쉽게.", "Keep the science accurate. Make the message clear."),
]


def main() -> None:
    ko_paths = []
    for index, (slug, ko, en) in enumerate(SERIES, 1):
        ko_path = OUT / f"{index:02d}-{slug}-ko.jpg"
        en_path = OUT / f"{index:02d}-{slug}-en.jpg"
        render_direction(slug, ko, "ko", ko_path)
        render_direction(slug, en, "en", en_path)
        ko_paths.append(ko_path)
    create_contact_sheet(ko_paths, OUT / "review-ko.jpg")
    print(OUT)


if __name__ == "__main__":
    main()
