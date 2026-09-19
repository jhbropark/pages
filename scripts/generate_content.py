#!/usr/bin/env python3
"""Write copy into content/buffer.json — the refill half of the pipeline.

This script does not render cards and does not touch the queues. It writes
copy, and scripts/render_daily.py turns that copy into cards on the day. The
split exists so the daily run needs no model: a lapsed key or an empty credit
balance delays a refill, which is visible days ahead, instead of silently
killing the daily post (as it did for 38 days from 2026-08-12).

The scheduled refill runs through .github/workflows/content-refill.yml, which
authenticates with a Claude subscription rather than API credits. This script
is the API-key path, for topping the buffer up by hand:

    ANTHROPIC_API_KEY=... python scripts/generate_content.py --days 7
"""

import json
import os
import sys
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).parent.parent
TOPICS_FILE = REPO_ROOT / "content" / "topics.json"
BUFFER_FILE = REPO_ROOT / "content" / "buffer.json"

MODEL = "claude-opus-5"

PAGES_BASE_URL = "https://jhbropark.github.io/pages"
RAW_BASE_URL = "https://raw.githubusercontent.com/jhbropark/pages/main"



def load_generation_config() -> dict:
    with open(TOPICS_FILE, encoding="utf-8") as f:
        return json.load(f)


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
    "- linkedin_ko: 공백 제외 최소 800자(넉넉히 900자 내외). 도입 → 핵심 논점 3가지(각 구체 사례·수치) → 결론 → CTA 구조로 충분히 길게. 짧으면 폐기되니 분량을 반드시 채울 것.\n"
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
        model=MODEL,
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
    if any(not str(tag).strip().startswith("#") for tag in hashtags):
        errors.append("모든 해시태그는 #으로 시작해야 합니다.")
    ko_count = len("".join(content.get("linkedin_ko", "").split()))
    if not 650 <= ko_count <= 1500:
        errors.append(f"LinkedIn 한국어 본문은 공백 제외 650~1500자여야 합니다: {ko_count}자")
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
        tags = content.get(field, [])
        if not 3 <= len(tags) <= 4:
            errors.append(f"{field}는 3~4개여야 합니다.")
        if any(not str(tag).strip().startswith("#") for tag in tags):
            errors.append(f"{field}의 모든 해시태그는 #으로 시작해야 합니다.")
    return errors


# ---------------------------------------------------------------------------
# 3. 버퍼에 쓰기
# ---------------------------------------------------------------------------

def load_buffer() -> dict:
    if not BUFFER_FILE.exists():
        return {"items": []}
    with open(BUFFER_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_buffer(buffer: dict) -> None:
    BUFFER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BUFFER_FILE, "w", encoding="utf-8") as f:
        json.dump(buffer, f, ensure_ascii=False, indent=2)
        f.write("\n")


def buffered_topics(buffer: dict) -> set[str]:
    """Topics already waiting in the buffer, so a refill does not repeat one."""
    return {item.get("topic", "") for item in buffer.get("items", [])
            if not item.get("consumed_at")}


def generate_one(config: dict, slot: dict, topic: str) -> dict:
    """One validated buffer item. Retries with the validator's own complaints."""
    errors: list[str] = []
    for attempt in range(1, 4):
        feedback = "- " + "\n- ".join(errors) if errors else ""
        content = generate_text(
            topic, config["brand_guide"], slot.get("editorial_focus", ""),
            feedback=feedback,
        )
        errors = validate_generated_content(content)
        if not errors:
            break
        print(f"  검증 실패(시도 {attempt}/3): {' / '.join(errors)}", flush=True)
    if errors:
        raise ValueError("생성 콘텐츠 검증 실패(3회 시도): " + " / ".join(errors))

    content["caption"] = build_conversion_caption(content)
    content["topic"] = topic
    content["generated_by"] = MODEL
    return content


def main() -> None:
    days = 7
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])

    config = load_generation_config()
    buffer = load_buffer()
    seen = buffered_topics(buffer)
    topics = [t for t in config["topics"] if t not in seen]
    slots = config["daily_slots"]

    wanted = days * len(slots)
    if not topics:
        print("모든 주제가 이미 버퍼에 있습니다. 추가할 것이 없습니다.", flush=True)
        return
    if len(topics) < wanted:
        print(f"남은 주제가 {len(topics)}개뿐이라 그만큼만 생성합니다.", flush=True)
        wanted = len(topics)

    added = 0
    for index in range(wanted):
        slot = slots[index % len(slots)]
        topic = topics[index]
        print(f"[{index + 1}/{wanted}] {slot['id']} — {topic}", flush=True)
        buffer.setdefault("items", []).append(generate_one(config, slot, topic))
        added += 1
        save_buffer(buffer)  # checkpoint, so a mid-run failure keeps what worked

    remaining = sum(1 for i in buffer["items"] if not i.get("consumed_at"))
    print(f"{added}개 추가. 버퍼 잔량 {remaining}개 ≈ {remaining // len(slots)}일치", flush=True)

    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"added={added}\n")
            f.write(f"buffer_remaining={remaining}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        print(f"버퍼 리필 실패: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
