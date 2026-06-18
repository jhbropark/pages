#!/usr/bin/env python3
"""
Instagram + LinkedIn 이중 언어 콘텐츠 자동 생성 스크립트

1. content/topics.json에서 오늘의 주제를 선택
2. Claude API로 B2B 캡션 + 해시태그 + 이미지 헤드라인 생성
3. 한국어·영어 이미지 카드 생성 (images/)
4. 매일 두 슬롯의 Instagram 한국어 큐와 LinkedIn 한국어→영어 쌍 큐에 추가

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
from visual_direction_renderer import render_direction

REPO_ROOT = Path(__file__).parent.parent
TOPICS_FILE = REPO_ROOT / "content" / "topics.json"
QUEUE_FILE = REPO_ROOT / "queue" / "queue.json"
LINKEDIN_QUEUE_FILE = REPO_ROOT / "linkedin" / "queue.json"
IMAGES_DIR = REPO_ROOT / "images"

KST = timezone(timedelta(hours=9))
PAGES_BASE_URL = "https://jhbropark.github.io/pages"
RAW_BASE_URL = "https://raw.githubusercontent.com/jhbropark/pages/main"

# 한글 폰트 후보 (GitHub Actions에서는 fonts-nanum 설치)
KOREAN_FONT_CANDIDATES = [
    "C:/Windows/Fonts/NotoSansKR-VF.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
]
FALLBACK_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]


# ---------------------------------------------------------------------------
# 1. 주제 선택
# ---------------------------------------------------------------------------

def load_generation_config() -> dict:
    with open(TOPICS_FILE, encoding="utf-8") as f:
        return json.load(f)


def pick_topic(config: dict, now_kst: datetime, slot_index: int) -> str:
    """날짜와 슬롯에 따라 겹치지 않는 주제를 순환 선택합니다."""
    topics = config["topics"]
    topic_index = (now_kst.timetuple().tm_yday * len(config["daily_slots"]) + slot_index) % len(topics)
    return topics[topic_index]


# ---------------------------------------------------------------------------
# 2. Claude API로 텍스트 생성
# ---------------------------------------------------------------------------

CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "caption": {
            "type": "string",
            "description": "Instagram 핵심 본문. 80~120자, 한국어, 해시태그와 CTA 제외",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "핵심 한국어/영어 해시태그 5~7개, 각각 #으로 시작",
        },
        "image_headline": {
            "type": "string",
            "description": "이미지 카드에 들어갈 핵심 문구. 한국어 10~24자, 전문적이고 명료하게",
        },
        "comment_question": {
            "type": "string",
            "description": "10초 안에 답할 수 있는 A/B 선택 또는 한 단어 댓글 질문. 35자 이내",
        },
        "dm_keyword": {
            "type": "string",
            "description": "DM으로 보낼 2~6자의 기억하기 쉬운 대문자 영문 또는 한국어 키워드",
        },
        "dm_offer": {
            "type": "string",
            "description": "DM 키워드를 보내면 제공할 체크리스트·진단 질문·가이드. 35자 이내",
        },
        "english_image_headline": {
            "type": "string",
            "description": "English image headline. Maximum 34 characters, concise and premium.",
        },
        "linkedin_ko": {
            "type": "string",
            "description": "LinkedIn 한국어 칼럼. 공백 제외 800~1500자. 마지막에 댓글 질문, DM 키워드와 문의 허브 안내 포함",
        },
        "linkedin_en": {
            "type": "string",
            "description": "English LinkedIn essay, 1200~2600 characters. Do not add a language label. End with a question, the same DM keyword, and the contact hub.",
        },
        "linkedin_ko_hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "linkedin_en_hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
    },
    "required": [
        "caption",
        "hashtags",
        "image_headline",
        "comment_question",
        "dm_keyword",
        "dm_offer",
        "english_image_headline",
        "linkedin_ko",
        "linkedin_en",
        "linkedin_ko_hashtags",
        "linkedin_en_hashtags",
    ],
    "additionalProperties": False,
}


REQUIREMENTS = (
    "\n\n[반드시 지켜야 하는 엄격한 분량·개수 요건 — 하나라도 어기면 폐기됩니다]\n"
    "- caption(핵심 본문): 한국어 80~100자. (시스템이 댓글/DM/링크 줄을 덧붙이므로 본문이 길면 전체가 220자를 넘김)\n"
    "- comment_question: 35자 이내. dm_keyword: 2~6자. dm_offer: 35자 이내.\n"
    "- hashtags: 정확히 5~7개, 각 항목 #으로 시작.\n"
    "- image_headline: 한국어 10~24자. english_image_headline: 영문 34자 이내.\n"
    "- linkedin_ko: 공백 제외 800~1500자(공백 포함이 아니라 공백을 뺀 글자 수 기준이니 넉넉히 길게).\n"
    "- linkedin_en: 1200~2600자. 'English version' 같은 표시 금지.\n"
    "- dm_keyword 문자열을 linkedin_ko 와 linkedin_en 본문 안에 각각 반드시 그대로 포함.\n"
    "- linkedin_ko_hashtags: 정확히 3~4개. linkedin_en_hashtags: 정확히 3~4개.\n"
)


def generate_text(
    topic: str, brand_guide: str, editorial_focus: str = "", feedback: str = ""
) -> dict:
    client = anthropic.Anthropic()
    user_content = (
        f"오늘의 주제: \"{topic}\"\n\n"
        f"이번 슬롯의 편집 방향: {editorial_focus}\n\n"
        "이 주제로 브랜드·마케팅·R&D·메디컬 담당자에게 "
        "실무적인 관점이나 판단 기준을 주는 Instagram 게시물을 작성해 주세요. "
        "복잡한 과학을 쉽게 전달하되 전문성을 낮추지 말고, "
        "서비스를 과도하게 광고하기보다 bbbb.beauty의 관점과 역량이 "
        "자연스럽게 드러나게 하세요. 소비자용 피부관리 팁은 작성하지 마세요. "
        "반드시 고객이 댓글과 DM으로 쉽게 대화를 시작할 수 있는 장치를 만드세요. "
        "댓글 질문은 A/B 선택이나 한 단어 답변처럼 부담이 없어야 하며, "
        "DM 키워드에는 받을 자료나 다음 단계를 구체적으로 연결하세요. "
        "같은 주제의 LinkedIn 한국어판과 영어판도 작성하세요. "
        "영어판은 번역투가 아닌 글로벌 B2B 의사결정자를 위한 자연스러운 "
        "에세이로 쓰고 'English version' 같은 언어 표시는 넣지 마세요. "
        "두 언어판은 같은 주장, 질문, DM 키워드, 문의 허브 "
        "https://jhbropark.github.io/pages/contact.html 을 사용하세요."
        + REQUIREMENTS
    )
    if feedback:
        user_content += (
            "\n\n[직전 시도가 요건을 위반했습니다. 아래를 반드시 교정해서 다시 작성하세요]\n"
            + feedback
        )
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=(
            "당신은 메디컬·더마·바이오·뷰티 분야 B2B 크리에이티브 "
            "에이전시의 과학 커뮤니케이션 에디터입니다. "
            f"브랜드 가이드: {brand_guide}"
        ),
        messages=[{"role": "user", "content": user_content}],
        output_config={"format": {"type": "json_schema", "schema": CONTENT_SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def build_conversion_caption(content: dict) -> str:
    """핵심 본문과 다중 CTA를 Instagram 길이 안에서 조합합니다."""
    return (
        f"{content['caption'].strip()}\n\n"
        f"댓글: {content['comment_question'].strip()}\n"
        f"DM “{content['dm_keyword'].strip()}”: {content['dm_offer'].strip()}\n"
        "프로필 링크에서 포트폴리오를 확인하고, 팀에 저장·공유해 주세요."
    )


def validate_generated_content(content: dict) -> list[str]:
    errors = []
    keyword = content.get("dm_keyword", "").strip()
    question = content.get("comment_question", "").strip()
    offer = content.get("dm_offer", "").strip()
    caption = build_conversion_caption(content)

    if not question:
        errors.append("댓글 질문이 없습니다.")
    if not 2 <= len(keyword) <= 6:
        errors.append("DM 키워드는 2~6자여야 합니다.")
    if not offer:
        errors.append("DM 제공 자료가 없습니다.")
    if len(caption) > 220:
        errors.append(f"CTA 포함 캡션이 220자를 초과합니다: {len(caption)}자")
    hashtags = content.get("hashtags", [])
    if not 5 <= len(hashtags) <= 7:
        errors.append("해시태그는 5~7개여야 합니다.")
    ko_count = len("".join(content.get("linkedin_ko", "").split()))
    if not 800 <= ko_count <= 1500:
        errors.append(f"LinkedIn 한국어 본문은 공백 제외 800~1500자여야 합니다: {ko_count}자")
    en_count = len(content.get("linkedin_en", "").strip())
    if not 1200 <= en_count <= 2600:
        errors.append(f"LinkedIn 영어 본문은 1200~2600자여야 합니다: {en_count}자")
    if content.get("linkedin_en", "").lstrip().lower().startswith("english version"):
        errors.append("LinkedIn 영어 본문에 'English version'을 넣지 마세요.")
    if keyword and keyword not in content.get("linkedin_ko", ""):
        errors.append("LinkedIn 한국어 본문에 DM 키워드가 없습니다.")
    if keyword and keyword not in content.get("linkedin_en", ""):
        errors.append("LinkedIn 영어 본문에 DM 키워드가 없습니다.")
    for field in ("linkedin_ko_hashtags", "linkedin_en_hashtags"):
        if not 3 <= len(content.get(field, [])) <= 4:
            errors.append(f"{field}는 3~4개여야 합니다.")
    return errors


# ---------------------------------------------------------------------------
# 3. 템플릿 이미지 생성 (Deep Navy + Soft Beige + Aqua Blue)
# ---------------------------------------------------------------------------

def _load_font(size: int, variation: str = "Regular") -> ImageFont.FreeTypeFont:
    for path in KOREAN_FONT_CANDIDATES:
        if Path(path).exists():
            loaded = ImageFont.truetype(path, size)
            try:
                loaded.set_variation_by_name(variation)
            except (AttributeError, OSError):
                pass
            return loaded
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

    headline_font = _load_font(70, "Regular")
    brand_font = _load_font(30, "Medium")

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


def generate_linkedin_image(
    headline: str,
    output_path: Path,
    seed: int,
    direction: str | None = None,
    language: str = "ko",
) -> None:
    """Create a 1200x627 LinkedIn card using a rotating visual direction."""
    if direction:
        render_direction(direction, headline, language, output_path)
        return

    width, height = 1200, 627
    image = Image.new("RGB", (width, height), (8, 20, 38))
    pixels = image.load()
    aqua = (14, 165, 233)
    beige = (248, 246, 242)
    for y in range(height):
        for x in range(width):
            gradient = (x * 0.22 + y) / (width * 0.22 + height)
            glow = max(
                0.0,
                1.0 - math.hypot(x - width * 0.82, y - height * 0.2) / 560,
            )
            pixels[x, y] = (
                int(8 + 22 * gradient + aqua[0] * glow * 0.04),
                int(20 + 24 * gradient + aqua[1] * glow * 0.12),
                int(38 + 28 * gradient + aqua[2] * glow * 0.15),
            )

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    for _ in range(7):
        cx = rng.randint(int(width * 0.58), width + 100)
        cy = rng.randint(-80, height + 80)
        radius = rng.randint(70, 190)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=(14, 165, 233, rng.randint(12, 30)),
            width=2,
        )
    draw.rounded_rectangle(
        (70, 70, 1130, 292),
        radius=28,
        fill=(8, 20, 38, 218),
        outline=(248, 246, 242, 45),
        width=1,
    )
    draw.rounded_rectangle((70, 70, 80, 292), radius=5, fill=(*aqua, 255))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)

    headline_font = _load_font(62, "Regular")
    meta_font = _load_font(20, "Regular")
    brand_font = _load_font(22, "Medium")
    lines = _wrap_headline(headline, max_chars=28)
    if len(lines) > 2:
        lines = lines[:2]
    for index, line in enumerate(lines):
        draw.text(
            (118, 108 + index * 78),
            line,
            font=headline_font,
            fill=beige,
        )
    draw.text(
        (120, 252),
        "SCIENCE TO MESSAGE · BEAUTY TO EXPERIENCE",
        font=meta_font,
        fill=(125, 211, 252),
    )
    draw.rounded_rectangle(
        (70, 538, 1130, 592),
        radius=18,
        fill=(8, 20, 38, 210),
        outline=(248, 246, 242, 38),
        width=1,
    )
    brand_width = draw.textlength("bbbb.beauty", font=brand_font)
    draw.text(
        ((width - brand_width) / 2, 552),
        "bbbb.beauty",
        font=brand_font,
        fill=beige,
    )
    image.convert("RGB").save(output_path, quality=94, optimize=True)


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


def add_linkedin_pair(items: list[dict]) -> None:
    """LinkedIn 큐에 한국어→영어 순서의 한 쌍을 추가합니다."""
    if [item.get("language") for item in items] != ["ko", "en"]:
        raise ValueError("LinkedIn 언어쌍은 ko, en 순서여야 합니다.")
    if len({item.get("pair_id") for item in items}) != 1:
        raise ValueError("LinkedIn 언어쌍은 같은 pair_id를 사용해야 합니다.")
    with open(LINKEDIN_QUEUE_FILE, encoding="utf-8") as f:
        queue = json.load(f)
    queue["items"].extend(items)
    with open(LINKEDIN_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def slot_exists(post_id: str) -> bool:
    with open(QUEUE_FILE, encoding="utf-8") as f:
        queue = json.load(f)
    return any(item["id"] == post_id for item in queue["items"])


def generate_slot(
    now_kst: datetime,
    config: dict,
    slot: dict,
    slot_index: int,
) -> bool:
    slot_id = slot["id"]
    post_id = f"post_{now_kst:%Y%m%d}_{slot_id}"
    if slot_exists(post_id):
        print(f"[{post_id}] 해당 슬롯 콘텐츠가 이미 존재합니다. 건너뜁니다.")
        return False

    topic = pick_topic(config, now_kst, slot_index)
    print(f"[{slot_id}] 오늘의 주제: {topic}")
    print("Claude API로 캡션 생성 중...")
    content = None
    errors: list[str] = []
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        feedback = "- " + "\n- ".join(errors) if errors else ""
        content = generate_text(
            topic,
            config["brand_guide"],
            slot.get("editorial_focus", ""),
            feedback=feedback,
        )
        errors = validate_generated_content(content)
        if not errors:
            break
        print(f"  검증 실패(시도 {attempt}/{max_attempts}): {' / '.join(errors)}")
    if errors:
        raise ValueError(
            f"생성 콘텐츠 CTA 검증 실패({max_attempts}회 시도): " + " / ".join(errors)
        )
    content["caption"] = build_conversion_caption(content)
    print(f"헤드라인: {content['image_headline']}")

    IMAGES_DIR.mkdir(exist_ok=True)
    image_filename = f"{post_id}_ko.jpg"
    linkedin_ko_image_filename = f"{post_id}_linkedin_ko.jpg"
    linkedin_en_image_filename = f"{post_id}_linkedin_en.jpg"
    print("한국어·영어 템플릿 이미지 생성 중...")
    generate_image(content["image_headline"], IMAGES_DIR / image_filename, seed=now_kst.timetuple().tm_yday)
    visual_directions = (
        "insight",
        "moa-craft",
        "industry-solution",
        "methodology",
        "portfolio",
        "philosophy",
    )
    visual_direction = visual_directions[
        (now_kst.timetuple().tm_yday * len(config["daily_slots"]) + slot_index)
        % len(visual_directions)
    ]
    generate_linkedin_image(
        content["image_headline"],
        IMAGES_DIR / linkedin_ko_image_filename,
        seed=now_kst.timetuple().tm_yday,
        direction=visual_direction,
        language="ko",
    )
    generate_linkedin_image(
        content["english_image_headline"],
        IMAGES_DIR / linkedin_en_image_filename,
        seed=now_kst.timetuple().tm_yday,
        direction=visual_direction,
        language="en",
    )

    scheduled = compute_scheduled_time(now_kst, slot["instagram_time_kst"])
    add_to_queue({
        "id": post_id,
        "status": "pending",
        "topic": topic,
        "format": "single_image",
        "slot": slot_id,
        "image_url": f"{RAW_BASE_URL}/images/{image_filename}",
        "caption": content["caption"],
        "hashtags": content["hashtags"],
        "scheduled_time": scheduled.isoformat(),
        "created_at": now_kst.isoformat(),
        "generated_by": "claude-opus-4-8",
    })
    linkedin_scheduled = compute_scheduled_time(
        now_kst,
        slot["linkedin_time_kst"],
    )
    pair_id = f"linkedin_{now_kst:%Y%m%d}_{slot_id}"
    common = {
        "pair_id": pair_id,
        "status": "pending",
        "topic": topic,
        "slot": slot_id,
        "scheduled_time": linkedin_scheduled.isoformat(),
        "created_at": now_kst.isoformat(),
        "generated_by": "claude-opus-4-8",
        "dm_keyword": content["dm_keyword"],
    }
    add_linkedin_pair([
        {
            **common,
            "id": f"{pair_id}_ko",
            "language": "ko",
            "pair_order": 1,
            "commentary": content["linkedin_ko"],
            "hashtags": content["linkedin_ko_hashtags"],
            "image_url": f"{RAW_BASE_URL}/images/{linkedin_ko_image_filename}",
            "alt_text": f"bbbb.beauty 한국어 카드: {content['image_headline']}",
        },
        {
            **common,
            "id": f"{pair_id}_en",
            "language": "en",
            "pair_order": 2,
            "commentary": content["linkedin_en"],
            "hashtags": content["linkedin_en_hashtags"],
            "image_url": f"{RAW_BASE_URL}/images/{linkedin_en_image_filename}",
            "alt_text": f"bbbb.beauty English card: {content['english_image_headline']}",
        },
    ])
    print(
        f"[{slot_id}] 큐에 추가 완료: Instagram 1개 "
        f"({scheduled.isoformat()}) + LinkedIn 언어쌍 2개 "
        f"({linkedin_scheduled.isoformat()})"
    )
    return True


def main() -> None:
    now_kst = datetime.now(tz=KST)
    config = load_generation_config()
    generated = 0
    for slot_index, slot in enumerate(config["daily_slots"]):
        generated += int(generate_slot(now_kst, config, slot, slot_index))
    print(f"오늘 생성된 슬롯: {generated}/{len(config['daily_slots'])}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"콘텐츠 생성 실패: {exc}", file=sys.stderr)
        sys.exit(1)
