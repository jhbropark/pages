#!/usr/bin/env python3
"""
Krea 산출물 저장 규칙 스캐폴딩·검증 스크립트

content/plans/20260620-krea-content-production.md의 §7(파이프라인 통합)에서
정한 저장 규칙을 코드로 강제한다.

저장 규칙
  images/krea/<batch>/<concept>/instagram-card-01.jpg ... (정사각형 1080x1080)
  images/krea/<batch>/<concept>/linkedin-ko.jpg          (가로 1200x627)
  images/krea/<batch>/<concept>/linkedin-en.jpg          (가로 1200x627)
  images/krea/<batch>/<concept>/reel.mp4                 (선택, moa 컨셉)
  images/krea/<batch>/manifest.json                      (기대 자산 목록)

사용법
  python scripts/scaffold_krea_assets.py            # 디렉터리 + manifest 생성
  python scripts/scaffold_krea_assets.py --check    # 실제 파일 존재·규격 검증

--check는 Pillow가 있으면 이미지 규격(픽셀 크기)도 확인하고, 없으면 파일
존재 여부만 검증한다.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
KREA_DIR = REPO_ROOT / "images" / "krea"

PILOT_BATCH = "20260620-pilot"

# 정사각형 Instagram, 가로 LinkedIn 규격은 strategy.json의 채널 규칙을 따른다.
INSTAGRAM_SIZE = (1080, 1080)
LINKEDIN_SIZE = (1200, 627)
INSTAGRAM_CARD_COUNT = 6

# 파일럿 4개 컨셉. dm_keyword와 pillar_id는 콘텐츠 초안과 1:1로 맞춘다.
PILOT_CONCEPTS = [
    {
        "slug": "ingredient-delivery",
        "pillar_id": "moa_craft",
        "dm_keyword": "MOA",
        "topic": "성분 전달의 가시화",
        "has_reel": True,
    },
    {
        "slug": "warm-science",
        "pillar_id": "science_communication",
        "dm_keyword": "LAB",
        "topic": "차갑지 않은 과학",
        "has_reel": False,
    },
    {
        "slug": "one-cell-one-change",
        "pillar_id": "moa_craft",
        "dm_keyword": "FILM",
        "topic": "하나의 세포, 하나의 변화",
        "has_reel": True,
    },
    {
        "slug": "industry-scene",
        "pillar_id": "industry_solution",
        "dm_keyword": "UX",
        "topic": "업종별 한 장면",
        "has_reel": False,
    },
]


def expected_assets(concept: dict) -> list[dict]:
    """한 컨셉이 가져야 할 자산 목록과 규격을 반환합니다."""
    assets = []
    for i in range(1, INSTAGRAM_CARD_COUNT + 1):
        assets.append(
            {
                "file": f"instagram-card-{i:02d}.jpg",
                "kind": "image",
                "size": list(INSTAGRAM_SIZE),
                "channel": "instagram",
            }
        )
    for lang in ("ko", "en"):
        assets.append(
            {
                "file": f"linkedin-{lang}.jpg",
                "kind": "image",
                "size": list(LINKEDIN_SIZE),
                "channel": "linkedin",
            }
        )
    if concept.get("has_reel"):
        assets.append(
            {
                "file": "reel.mp4",
                "kind": "video",
                "size": None,
                "channel": "instagram",
            }
        )
    return assets


def build_manifest(batch: str, concepts: list[dict]) -> dict:
    """배치 전체의 기대 자산 manifest를 만듭니다."""
    return {
        "batch": batch,
        "source_tool": "krea",
        "plan": "content/plans/20260620-krea-content-production.md",
        "concepts": [
            {
                "slug": c["slug"],
                "pillar_id": c["pillar_id"],
                "dm_keyword": c["dm_keyword"],
                "topic": c["topic"],
                "assets": expected_assets(c),
            }
            for c in concepts
        ],
    }


def scaffold_batch(batch: str, concepts: list[dict]) -> Path:
    """배치 디렉터리와 컨셉별 하위 디렉터리, manifest.json을 생성합니다."""
    batch_dir = KREA_DIR / batch
    for concept in concepts:
        (batch_dir / concept["slug"]).mkdir(parents=True, exist_ok=True)
    manifest_path = batch_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(build_manifest(batch, concepts), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return batch_dir


def _image_size(path: Path):
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as img:
            return img.size
    except OSError:
        return "unreadable"


def check_batch(batch: str) -> list[str]:
    """manifest 기준으로 실제 파일의 존재와 규격을 검증해 문제 목록을 반환합니다."""
    batch_dir = KREA_DIR / batch
    manifest_path = batch_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"manifest가 없습니다: {manifest_path}. 먼저 스캐폴딩을 실행하세요."]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = []
    for concept in manifest["concepts"]:
        for asset in concept["assets"]:
            path = batch_dir / concept["slug"] / asset["file"]
            if not path.exists():
                problems.append(f"누락: {path.relative_to(REPO_ROOT)}")
                continue
            if asset["kind"] == "image" and asset["size"]:
                size = _image_size(path)
                if size is None:
                    continue  # Pillow 미설치 — 존재만 확인
                if size == "unreadable":
                    problems.append(f"열 수 없음: {path.relative_to(REPO_ROOT)}")
                elif list(size) != asset["size"]:
                    problems.append(
                        f"규격 불일치: {path.relative_to(REPO_ROOT)} "
                        f"기대 {asset['size']}, 실제 {list(size)}"
                    )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Krea 산출물 저장 스캐폴딩·검증")
    parser.add_argument(
        "--batch", default=PILOT_BATCH, help=f"배치 이름 (기본: {PILOT_BATCH})"
    )
    parser.add_argument(
        "--check", action="store_true", help="생성 대신 실제 파일을 검증"
    )
    args = parser.parse_args()

    if args.check:
        problems = check_batch(args.batch)
        if problems:
            print(f"[{args.batch}] 검증 실패 {len(problems)}건:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"[{args.batch}] 모든 기대 자산이 규격을 만족합니다.")
        return 0

    batch_dir = scaffold_batch(args.batch, PILOT_CONCEPTS)
    print(f"스캐폴딩 완료: {batch_dir.relative_to(REPO_ROOT)}")
    print("컨셉별 디렉터리와 manifest.json을 생성했습니다.")
    print("Krea 산출물을 manifest의 파일명 규칙에 맞춰 저장한 뒤 --check로 검증하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
