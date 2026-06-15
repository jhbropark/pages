#!/usr/bin/env python3
"""Create 2026-06-16 Instagram carousel and bilingual LinkedIn posts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from visual_direction_renderer import render_direction


ROOT = Path(__file__).parent.parent
OUT = ROOT / "images" / "daily" / "20260616-data-understanding"
IG_QUEUE = ROOT / "queue" / "queue.json"
LI_QUEUE = ROOT / "linkedin" / "queue.json"
RAW = "https://raw.githubusercontent.com/jhbropark/pages/main"
FONT_SANS = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_SERIF = Path("C:/Windows/Fonts/NotoSerifKR-VF.ttf")
FONT_LATIN = Path("C:/Windows/Fonts/bahnschrift.ttf")
W, H = 1080, 1350

SOURCES = [
    ROOT / "images" / "concepts" / "visual-directions-v3" / "04-data-minimal-source.png",
    ROOT / "images" / "tests" / "scientific-choreography" / "02-translation-source.png",
    ROOT / "images" / "concepts" / "visual-directions-v3" / "01-hyper-silico-source.png",
    ROOT / "images" / "concepts" / "visual-directions-v3" / "02-neo-lab-source.png",
    ROOT / "images" / "replacements" / "body-cell-narrative" / "05-multi-channel-source.png",
]


def font(size: int, *, serif: bool = False, latin: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_LATIN if latin else FONT_SERIF if serif else FONT_SANS
    return ImageFont.truetype(str(path), size)


def cover(path: Path, size: tuple[int, int], bias_x: float = 0.5, bias_y: float = 0.5) -> Image.Image:
    image = Image.open(path).convert("RGB")
    ratio = max(size[0] / image.width, size[1] / image.height)
    image = image.resize(
        (round(image.width * ratio), round(image.height * ratio)),
        Image.Resampling.LANCZOS,
    )
    left = round((image.width - size[0]) * bias_x)
    top = round((image.height - size[1]) * bias_y)
    return image.crop((left, top, left + size[0], top + size[1]))


def fit_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_lines: int,
    start_size: int,
    *,
    serif: bool = False,
) -> tuple[list[str], ImageFont.FreeTypeFont]:
    words = text.replace("\n", " \n ").split()
    chosen_lines: list[str] = []
    chosen_font = font(start_size, serif=serif)
    for size in range(start_size, 31, -2):
        current_font = font(size, serif=serif)
        lines: list[str] = []
        line = ""
        for word in words:
            if word == "\n":
                if line:
                    lines.append(line)
                    line = ""
                continue
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=current_font) <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        chosen_lines, chosen_font = lines, current_font
        if len(lines) <= max_lines:
            break
    return chosen_lines[:max_lines], chosen_font


def footer(draw: ImageDraw.ImageDraw, dark: bool = True) -> None:
    color = (248, 246, 239) if dark else (22, 24, 26)
    draw.text((58, 1270), "bbbb.beauty", font=font(25, latin=True), fill=color)
    draw.text((58, 1305), "Science to Message, Beauty to Experience.", font=font(18, latin=True), fill=color)


def render_card(
    index: int,
    title: str,
    subtitle: str,
    style: str,
    output: Path,
) -> None:
    if style == "signal":
        image = Image.new("RGB", (W, H), (235, 255, 46))
        visual = cover(SOURCES[0], (W, 720), 0.62)
        image.paste(visual, (0, 630))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, W, 665), fill=(235, 255, 46))
        for x in range(54, W, 54):
            draw.line((x, 0, x, 665), fill=(190, 205, 40), width=1)
        draw.text((64, 70), "01 / DATA DOES NOT PERSUADE ALONE", font=font(24, latin=True), fill=(24, 26, 28))
        lines, title_font = fit_lines(draw, title, 760, 4, 82, serif=True)
        y = 210
        for line in lines:
            draw.text((64, y), line, font=title_font, fill=(20, 22, 24))
            y += round(title_font.size * 1.2)
        draw.ellipse((825, 515, 885, 575), fill=(236, 47, 54))
        footer(draw, dark=False)
    elif style == "translation":
        image = cover(SOURCES[1], (W, H), 0.45).convert("RGBA")
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle((0, 0, W, H), fill=(250, 246, 238, 0))
        draw.rectangle((0, 0, 505, H), fill=(246, 242, 235, 236))
        draw.rectangle((64, 82, 88, 230), fill=(231, 62, 53))
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)
        draw.text((118, 84), "02 / ORDER OF UNDERSTANDING", font=font(23, latin=True), fill=(24, 22, 20))
        lines, title_font = fit_lines(draw, title, 355, 4, 66, serif=True)
        y = 295
        for line in lines:
            draw.text((64, y), line, font=title_font, fill=(28, 26, 24))
            y += round(title_font.size * 1.18)
        draw.line((64, 1040, 430, 1040), fill=(28, 26, 24), width=2)
        draw.text((64, 1065), subtitle, font=font(29), fill=(72, 66, 60))
        footer(draw, dark=False)
        image = image.convert("RGB")
    elif style == "mechanism":
        image = ImageEnhance.Contrast(cover(SOURCES[2], (W, H), 0.55)).enhance(1.1).convert("RGBA")
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle((0, 0, W, H), fill=(0, 12, 22, 62))
        draw.rectangle((0, 735, W, H), fill=(2, 12, 20, 220))
        draw.rectangle((0, 0, 22, H), fill=(80, 218, 255, 255))
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)
        draw.text((64, 78), "03 / MECHANISM AS SEQUENCE", font=font(24, latin=True), fill=(218, 244, 250))
        lines, title_font = fit_lines(draw, title, 900, 3, 70)
        y = 810
        for line in lines:
            draw.text((64, y), line, font=title_font, fill=(248, 246, 239))
            y += round(title_font.size * 1.12)
        draw.text((64, 1115), subtitle, font=font(30), fill=(190, 230, 242))
        footer(draw, dark=True)
        image = image.convert("RGB")
    elif style == "lab":
        image = cover(SOURCES[3], (W, H), 0.48).filter(ImageFilter.GaussianBlur(0.25)).convert("RGBA")
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle((0, 0, W, 735), fill=(250, 247, 241, 232))
        draw.rectangle((0, 735, W, 750), fill=(145, 100, 214, 255))
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)
        draw.text((64, 80), "04 / VISUAL TRANSLATION", font=font(24, latin=True), fill=(87, 59, 116))
        lines, title_font = fit_lines(draw, title, 810, 4, 70, serif=True)
        y = 220
        for line in lines:
            draw.text((64, y), line, font=title_font, fill=(30, 27, 32))
            y += round(title_font.size * 1.15)
        draw.text((64, 610), subtitle, font=font(31), fill=(75, 68, 78))
        footer(draw, dark=True)
        image = image.convert("RGB")
    else:
        image = Image.new("RGB", (W, H), (13, 11, 11))
        visual = cover(SOURCES[4], (W, 720), 0.5)
        image.paste(visual, (0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, W, 720), outline=(255, 101, 67), width=8)
        draw.rectangle((0, 720, W, H), fill=(13, 11, 11))
        draw.text((64, 770), "05 / PROJECT INQUIRY", font=font(24, latin=True), fill=(255, 101, 67))
        lines, title_font = fit_lines(draw, title, 900, 3, 62)
        y = 850
        for line in lines:
            draw.text((64, y), line, font=title_font, fill=(246, 239, 228))
            y += round(title_font.size * 1.12)
        draw.text((64, 1130), subtitle, font=font(30), fill=(222, 214, 204))
        footer(draw, dark=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95, optimize=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert_item(items: list[dict], item: dict) -> None:
    for index, existing in enumerate(items):
        if existing.get("id") == item["id"]:
            items[index] = item
            return
    items.append(item)


def disable_old_pending(items: list[dict], ids: set[str]) -> None:
    for item in items:
        if item.get("id") in ids and item.get("status") == "pending":
            item["status"] = "replaced"
            item["replacement_reason"] = "Replaced by 2026-06-16 data-understanding content"


def main() -> None:
    cards = [
        ("데이터는 충분한데\n왜 설득되지 않을까요?", "정보량보다 이해의 순서가 먼저입니다.", "signal"),
        ("고객은 숫자보다 먼저\n변화를 이해합니다.", "변화가 보이면 근거가 읽힙니다.", "translation"),
        ("작용 원리는\n순서로 보여줘야 합니다.", "이동, 결합, 반응을 장면으로 연결합니다.", "mechanism"),
        ("bbbb.beauty는 데이터를\n장면으로 번역합니다.", "과학적 정확성과 프리미엄 비주얼을 함께 설계합니다.", "lab"),
        ("설명하기 어려운 기술이 있다면\n프로젝트 배경을 남겨주세요.", "프로필 링크에서 제작 목적과 자료 범위를 알려주세요.", "portfolio"),
    ]
    image_paths = []
    for index, (title, subtitle, style) in enumerate(cards, 1):
        path = OUT / f"instagram-carousel-{index:02d}.jpg"
        render_card(index, title, subtitle, style, path)
        image_paths.append(path)

    linkedin_ko_image = OUT / "linkedin-ko.jpg"
    linkedin_en_image = OUT / "linkedin-en.jpg"
    render_direction("industry-solution", "임상 데이터가 많아도 고객이 이해하지 못하는 이유", "ko", linkedin_ko_image)
    render_direction("industry-solution", "Why more clinical data does not always create understanding", "en", linkedin_en_image)

    now = datetime.now(tz=timezone.utc).isoformat()

    ig_queue = load_json(IG_QUEUE)
    disable_old_pending(ig_queue["items"], {"post_20260616"})
    ig_item = {
        "id": "post_20260616_data_understanding_carousel",
        "status": "pending",
        "topic": "임상 데이터는 충분한데 고객은 왜 이해하지 못할까",
        "pillar_id": "science_communication",
        "format": "carousel",
        "image_urls": [
            f"{RAW}/images/daily/20260616-data-understanding/{path.name}"
            for path in image_paths
        ],
        "caption": (
            "데이터가 많아도 고객이 기술의 차이를 이해하지 못한다면, 문제는 자료의 양이 아닐 수 있습니다.\n\n"
            "고객은 숫자보다 먼저 변화의 장면을 이해합니다. 그다음 작용 원리와 근거를 확인합니다. "
            "bbbb.beauty는 복잡한 메디컬·바이오 기술을 고객이 이해할 수 있는 3D/MoA 장면과 인터랙티브 경험으로 번역합니다.\n\n"
            "현재 가장 설명하기 어려운 것은 임상 그래프인가요, 작용 기전인가요? "
            "프로필 링크에서 프로젝트 배경과 자료 범위를 남겨주세요."
        ),
        "hashtags": [
            "#과학커뮤니케이션",
            "#메디컬애니메이션",
            "#더마코스메틱",
            "#바이오마케팅",
            "#3DMOA",
            "#bbbbbeauty",
        ],
        "scheduled_time": "2026-06-16T19:00:00+09:00",
        "created_at": now,
        "generated_by": "codex-20260616-data-understanding",
    }
    upsert_item(ig_queue["items"], ig_item)
    save_json(IG_QUEUE, ig_queue)

    li_queue = load_json(LI_QUEUE)
    disable_old_pending(li_queue["items"], {"linkedin_20260616"})
    pair_id = "linkedin_20260616_data_understanding"
    ko_body = (
        "임상 데이터가 많아도 고객이 기술의 차이를 이해하지 못하는 경우가 있습니다.\n\n"
        "이때 문제는 데이터가 부족해서가 아닙니다. 고객이 어떤 순서로 이해해야 하는지가 설계되지 않았기 때문입니다.\n\n"
        "더마코스메틱, 제약, 바이오, 의료기기 브랜드의 자료에는 성분명, 작용 기전, 임상 그래프, 특허 정보가 함께 들어갑니다. "
        "각각은 중요한 근거지만, 고객은 모든 정보를 동시에 해석하지 않습니다. 먼저 무엇이 달라지는지 보고, 그 변화가 왜 일어나는지 이해한 뒤, 마지막으로 근거를 확인합니다.\n\n"
        "따라서 과학 콘텐츠는 정보의 양보다 이해의 순서를 먼저 설계해야 합니다.\n\n"
        "▪ 고객이 체감할 변화를 먼저 보여줍니다.\n"
        "▪ 그 변화를 만드는 작용 기전을 장면 단위로 연결합니다.\n"
        "▪ 임상과 연구 근거는 판단이 필요한 순간에 제시합니다.\n\n"
        "저희는 R&D 자료를 단순히 줄이지 않습니다. 복잡한 메디컬·바이오 기술을 고객이 이해할 수 있는 3D/MoA 영상, 과학 시각화, 인터랙티브 콘텐츠로 번역합니다. "
        "정확한 과학이 고객의 신뢰와 선택으로 이어지려면, 데이터의 양보다 장면의 순서가 먼저 결정되어야 합니다.\n\n"
        "이 접근은 상세페이지, 학회 부스, 세일즈 미팅, 투자자 설명 자료에서 모두 다르게 적용됩니다. 같은 근거라도 고객이 처음 접하는 채널에서는 변화의 장면이 먼저 필요하고, 전문가가 검토하는 자료에서는 작용 기전과 근거의 연결이 더 중요합니다. 그래서 하나의 데이터를 하나의 이미지로 고정하지 않고, 목적과 채널에 맞는 이해 구조로 다시 설계해야 합니다.\n\n"
        "현재 귀사의 자료에서 가장 설명하기 어려운 것은 임상 그래프인가요, 작용 기전인가요? 댓글이나 프로젝트 문의로 알려주시면 적합한 시각화 방향을 함께 검토하겠습니다.\n\n"
        "프로젝트 문의: https://jhbropark.github.io/pages/contact.html"
    )
    en_body = (
        "More clinical data does not always create better understanding.\n\n"
        "When customers still cannot understand the difference after more graphs, terms, and evidence are added, the problem may not be a lack of information. It may be the order in which the information is presented.\n\n"
        "Dermocosmetic, pharmaceutical, biotech, and medical-device materials often contain ingredient names, mechanisms of action, clinical graphs, and patent information at the same time. Each element matters, but customers do not process all of it simultaneously. They first need to see what changes, then understand why it changes, and finally examine the evidence that supports the claim.\n\n"
        "Scientific content should therefore begin with the order of understanding, not the amount of information.\n\n"
        "▪ Show the customer-relevant change first.\n"
        "▪ Connect the mechanism in a sequence of visual scenes.\n"
        "▪ Introduce clinical and research evidence at the moment it supports a decision.\n\n"
        "bbbb.beauty does not simply simplify R&D material. We translate complex medical and biotechnology concepts into 3D/MoA films, scientific visualizations, and interactive content that customers can understand and trust. Accurate science becomes persuasive when its visual sequence is designed before its information density.\n\n"
        "Which is harder to explain in your current material: the clinical graph or the mechanism of action? Share it in the comments or send us the project context, and we will review the appropriate visual direction with you.\n\n"
        "Project inquiry: https://jhbropark.github.io/pages/contact.html"
    )
    linkedin_items = [
        {
            "id": f"{pair_id}_ko",
            "pair_id": pair_id,
            "language": "ko",
            "pair_order": 1,
            "status": "pending",
            "pillar_id": "science_communication",
            "content_type": "daily-insight",
            "topic": "임상 데이터가 많아도 고객이 이해하지 못하는 이유",
            "commentary": ko_body,
            "hashtags": ["#과학커뮤니케이션", "#메디컬애니메이션", "#바이오마케팅", "#bbbbbeauty"],
            "image_url": f"{RAW}/images/daily/20260616-data-understanding/{linkedin_ko_image.name}",
            "alt_text": "임상 데이터보다 이해의 순서를 먼저 설계해야 한다는 bbbb.beauty LinkedIn 카드",
            "scheduled_time": "2026-06-16T09:00:00+09:00",
            "created_at": now,
            "generated_by": "codex-20260616-data-understanding",
        },
        {
            "id": f"{pair_id}_en",
            "pair_id": pair_id,
            "language": "en",
            "pair_order": 2,
            "status": "pending",
            "pillar_id": "science_communication",
            "content_type": "daily-insight",
            "topic": "Why more clinical data does not always create understanding",
            "commentary": en_body,
            "hashtags": ["#ScienceCommunication", "#MedicalAnimation", "#BiotechMarketing", "#bbbbbeauty"],
            "image_url": f"{RAW}/images/daily/20260616-data-understanding/{linkedin_en_image.name}",
            "alt_text": "bbbb.beauty LinkedIn card about designing the order of understanding before adding more clinical data",
            "scheduled_time": "2026-06-16T10:30:00+09:00",
            "created_at": now,
            "generated_by": "codex-20260616-data-understanding",
        },
    ]
    for item in linkedin_items:
        upsert_item(li_queue["items"], item)
    save_json(LI_QUEUE, li_queue)
    print(OUT)


if __name__ == "__main__":
    main()
