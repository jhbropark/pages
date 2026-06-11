#!/usr/bin/env python3
"""
Instagram 콘텐츠 자동 생성 스크립트

1. content/topics.json에서 오늘의 주제를 선택
2. Claude API로 B2B 캡션 + 해시태그 + 이미지 헤드라인 생성
3. Pillow로 메디컬 크리에이티브 브랜드 카드 생성 (images/)
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
    "C:/Windows/Fonts/NotoSansKR-VF.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
]
FALLBACK_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]


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
            "description": "이미지 카드에 들어갈 핵심 문구. 한국어 10~24자, 전문적이고 명료하게",
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
            "당신은 메디컬·더마·바이오·뷰티 분야 B2B 크리에이티브 "
            "에이전시의 과학 커뮤니케이션 에디터입니다. "
            f"브랜드 가이드: {brand_guide}"
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"오늘의 주제: \"{topic}\"\n\n"
                    "이 주제로 브랜드·마케팅·R&D·메디컬 담당자에게 "
                    "실무적인 관점이나 판단 기준을 주는 Instagram 게시물을 작성해 주세요. "
                    "복잡한 과학을 쉽게 전달하되 전문성을 낮추지 말고, "
                    "서비스를 과도하게 광고하기보다 bbbb.beauty의 관점과 역량이 "
                    "자연스럽게 드러나게 하세요. 소비자용 피부관리 팁은 작성하지 마세요."
                ),
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": CONTENT_SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# ---------------------------------------------------------------------------
# 3. 템플릿 이미지 생성 (Deep Navy + Soft Beige + Aqua Blue)
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in KOREAN_FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    for path in FALLBACK_FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


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

    c1 = (30, 41, 59)      # Deep Navy
    c2 = (248, 246, 242)   # Pure Soft Beige
    c3 = (14, 165, 233)    # Clear Aqua Blue
    for y in range(H):
        for x in range(W):
            t = (x * 0.35 + y) / (W * 0.35 + H)
            glow = max(0.0, 1.0 - math.hypot(x - W * 0.82, y - H * 0.18) / 700)
            r = int(c1[0] * (1 - t) + c2[0] * t + c3[0] * glow * 0.04)
            g = int(c1[1] * (1 - t) + c2[1] * t + c3[1] * glow * 0.12)
            b = int(c1[2] * (1 - t) + c2[2] * t + c3[2] * glow * 0.16)
            px[x, y] = (min(r, 255), min(g, 255), min(b, 255))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    for _ in range(9):
        cx, cy = rng.randint(0, W), rng.randint(0, H)
        rad = rng.randint(80, 220)
        alpha = rng.randint(10, 24)
        od.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(14, 165, 233, alpha), width=3)
    od.line([(80, 120), (420, 120)], fill=(14, 165, 233, 210), width=8)
    od.line([(80, 135), (260, 135)], fill=(248, 246, 242, 80), width=2)
    overlay = overlay.filter(ImageFilter.GaussianBlur(1))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    d = ImageDraw.Draw(img)
    text_color = (248, 246, 242)
    sub_color = (14, 165, 233)

    headline_font = _load_font(70)
    brand_font = _load_font(30)

    def center_text(y: float, text: str, font: ImageFont.FreeTypeFont, fill) -> None:
        bbox = d.textbbox((0, 0), text, font=font)
        d.text(((W - (bbox[2] - bbox[0])) / 2, y), text, font=font, fill=fill)

    lines = _wrap_headline(headline)
    line_height = 110
    start_y = H / 2 - line_height * len(lines) / 2 - 20

    panel_top = int(start_y - 120)
    panel_bottom = int(start_y + len(lines) * line_height + 180)
    d.rounded_rectangle(
        [(105, panel_top), (W - 105, panel_bottom)],
        radius=36,
        fill=(30, 41, 59, 218),
        outline=(14, 165, 233, 110),
        width=2,
    )
    center_text(175, "SCIENCE TO MESSAGE", brand_font, (125, 211, 252))
    d.line([(W / 2 - 70, start_y - 70), (W / 2 + 70, start_y - 70)], fill=sub_color, width=4)
    for i, line in enumerate(lines):
        center_text(start_y + i * line_height, line, headline_font, text_color)
    bottom = start_y + len(lines) * line_height + 40
    d.line([(W / 2 - 60, bottom), (W / 2 + 60, bottom)], fill=sub_color, width=3)
    center_text(bottom + 50, "bbbb.beauty", brand_font, text_color)
    center_text(bottom + 98, "Beauty to Experience.", _load_font(23), sub_color)

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
