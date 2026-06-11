#!/usr/bin/env python3
"""
Instagram 콘텐츠 자동 생성 스크립트

1. content/topics.json에서 오늘의 주제를 선택
2. Claude API로 캡션 + 해시태그 + 이미지 헤드라인 생성
3. Pillow로 브랜드 템플릿 이미지 생성 (images/)
4. queue/queue.json에 pending 항목 추가

필요한 환경 변수:
  ANTHROPIC_API_KEY - Claude API 키
"""

import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).parent.parent
TOPICS_FILE = REPO_ROOT / "content" / "topics.json"
QUEUE_FILE = REPO_ROOT / "queue" / "queue.json"
IMAGES_DIR = REPO_ROOT / "images"

KST = timezone(timedelta(hours=9))
PAGES_BASE_URL = "https://jhbropark.github.io/pages"

# 한글 폰트 후보 (GitHub Actions에서는 fonts-nanum 설치)
KOREAN_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
]
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


# ---------------------------------------------------------------------------
# 1. 주제 선택
# ---------------------------------------------------------------------------

def pick_topic(now_kst: datetime) -> tuple[str, str, str]:
    """오늘의 주제, 브랜드 가이드, 예약 시각(HH:MM)을 반환합니다."""
    with open(TOPICS_FILE, encoding="utf-8") as f:
        config = json.load(f)
    topics = config["topics"]
    topic = topics[now_kst.timetuple().tm_yday % len(topics)]
    return topic, config["brand_guide"], config.get("schedule_time_kst", "18:00")


# ---------------------------------------------------------------------------
# 2. Claude API로 텍스트 생성
# ---------------------------------------------------------------------------

CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "caption": {
            "type": "string",
            "description": "Instagram 게시물 본문. 300~600자, 한국어, 줄바꿈 포함, 해시태그 제외",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "한국어/영어 해시태그 8~12개, 각각 #으로 시작",
        },
        "image_headline": {
            "type": "string",
            "description": "이미지 카드에 들어갈 핵심 문구. 한국어 8~16자, 임팩트 있게",
        },
    },
    "required": ["caption", "hashtags", "image_headline"],
    "additionalProperties": False,
}


def generate_text(topic: str, brand_guide: str) -> dict:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=(
            "당신은 뷰티 브랜드의 Instagram 콘텐츠 에디터입니다. "
            f"브랜드 가이드: {brand_guide}"
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"오늘의 주제: \"{topic}\"\n\n"
                    "이 주제로 Instagram 게시물을 작성해 주세요. "
                    "실용적인 팁이나 정보를 담아 팔로워에게 도움이 되도록 하고, "
                    "브랜드 톤앤매너를 지켜주세요."
                ),
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": CONTENT_SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# ---------------------------------------------------------------------------
# 3. 템플릿 이미지 생성 (브랜드 스타일: 로즈 핑크 그라데이션 + 보케)
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in KOREAN_FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.truetype(FALLBACK_FONT, size)


def _wrap_headline(headline: str, max_chars: int = 9) -> list[str]:
    """헤드라인을 2줄 이내로 자연스럽게 나눕니다."""
    if len(headline) <= max_chars:
        return [headline]
    words = headline.split()
    if len(words) >= 2:
        mid = len(words) // 2 + len(words) % 2
        return [" ".join(words[:mid]), " ".join(words[mid:])]
    mid = len(headline) // 2
    return [headline[:mid], headline[mid:]]


def generate_image(headline: str, output_path: Path, seed: int) -> None:
    W = H = 1080
    img = Image.new("RGB", (W, H))
    px = img.load()

    c1 = (244, 194, 194)   # rose pink
    c2 = (255, 245, 235)   # cream ivory
    c3 = (230, 200, 215)   # soft mauve
    for y in range(H):
        for x in range(W):
            t = (x + y) / (W + H)
            u = math.sin(t * math.pi)
            r = int(c1[0] * (1 - t) + c2[0] * t + (c3[0] - c2[0]) * u * 0.25)
            g = int(c1[1] * (1 - t) + c2[1] * t + (c3[1] - c2[1]) * u * 0.25)
            b = int(c1[2] * (1 - t) + c2[2] * t + (c3[2] - c2[2]) * u * 0.25)
            px[x, y] = (min(r, 255), min(g, 255), min(b, 255))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    for _ in range(14):
        cx, cy = rng.randint(0, W), rng.randint(0, H)
        rad = rng.randint(60, 240)
        alpha = rng.randint(14, 38)
        od.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(255, 255, 255, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    d = ImageDraw.Draw(img)
    text_color = (105, 72, 88)
    sub_color = (140, 105, 118)

    headline_font = _load_font(76)
    brand_font = _load_font(34)

    def center_text(y: float, text: str, font: ImageFont.FreeTypeFont, fill) -> None:
        bbox = d.textbbox((0, 0), text, font=font)
        d.text(((W - (bbox[2] - bbox[0])) / 2, y), text, font=font, fill=fill)

    lines = _wrap_headline(headline)
    line_height = 110
    start_y = H / 2 - line_height * len(lines) / 2 - 20

    d.line([(W / 2 - 60, start_y - 70), (W / 2 + 60, start_y - 70)], fill=sub_color, width=3)
    for i, line in enumerate(lines):
        center_text(start_y + i * line_height, line, headline_font, text_color)
    bottom = start_y + len(lines) * line_height + 40
    d.line([(W / 2 - 60, bottom), (W / 2 + 60, bottom)], fill=sub_color, width=3)
    center_text(bottom + 50, "bbbb.beauty", brand_font, sub_color)

    img.convert("RGB").save(output_path, quality=92)


# ---------------------------------------------------------------------------
# 4. 큐에 항목 추가
# ---------------------------------------------------------------------------

def compute_scheduled_time(now_kst: datetime, time_str: str) -> datetime:
    """예약 시각 계산: 오늘 지정 시각, 이미 임박했으면 다음 날 같은 시각."""
    hour, minute = (int(x) for x in time_str.split(":"))
    target = now_kst.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target < now_kst + timedelta(hours=2):
        target += timedelta(days=1)
    return target


def add_to_queue(item: dict) -> None:
    with open(QUEUE_FILE, encoding="utf-8") as f:
        queue = json.load(f)
    queue["items"].append(item)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    now_kst = datetime.now(tz=KST)
    post_id = f"post_{now_kst:%Y%m%d}"

    # 같은 날 중복 생성 방지
    with open(QUEUE_FILE, encoding="utf-8") as f:
        queue = json.load(f)
    if any(item["id"] == post_id for item in queue["items"]):
        print(f"[{post_id}] 오늘 콘텐츠가 이미 존재합니다. 종료합니다.")
        return

    topic, brand_guide, schedule_time = pick_topic(now_kst)
    print(f"오늘의 주제: {topic}")

    print("Claude API로 캡션 생성 중...")
    content = generate_text(topic, brand_guide)
    print(f"헤드라인: {content['image_headline']}")

    IMAGES_DIR.mkdir(exist_ok=True)
    image_filename = f"{post_id}.jpg"
    print("템플릿 이미지 생성 중...")
    generate_image(content["image_headline"], IMAGES_DIR / image_filename, seed=now_kst.timetuple().tm_yday)

    scheduled = compute_scheduled_time(now_kst, schedule_time)
    add_to_queue({
        "id": post_id,
        "status": "pending",
        "topic": topic,
        "image_url": f"{PAGES_BASE_URL}/images/{image_filename}",
        "caption": content["caption"],
        "hashtags": content["hashtags"],
        "scheduled_time": scheduled.isoformat(),
        "created_at": now_kst.isoformat(),
        "generated_by": "claude-opus-4-8",
    })
    print(f"큐에 추가 완료: {post_id} (예약: {scheduled.isoformat()})")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"콘텐츠 생성 실패: {exc}", file=sys.stderr)
        sys.exit(1)
