#!/usr/bin/env python3
"""Render and queue six Instagram formats and six bilingual LinkedIn types."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "images" / "social-formats" / "body-cell-motion" / "source"
OUT = ROOT / "images" / "channel-six-types"
IG_QUEUE = ROOT / "queue" / "queue.json"
LI_QUEUE = ROOT / "linkedin" / "queue.json"
RAW = "https://raw.githubusercontent.com/jhbropark/pages/main"
PAGES = "https://jhbropark.github.io/pages"
FONT = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
IVORY = (248, 243, 235)
CORAL = (255, 99, 76)
AMBER = (255, 188, 92)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def cover(source: Image.Image, size: tuple[int, int], bias: float = 0.5):
    width, height = size
    ratio = max(width / source.width, height / source.height)
    resized = source.resize(
        (round(source.width * ratio), round(source.height * ratio)),
        Image.Resampling.LANCZOS,
    )
    left = round(max(0, resized.width - width) * bias)
    top = round(max(0, resized.height - height) * 0.5)
    return resized.crop((left, top, left + width, top + height))


def background(index: int, size: tuple[int, int]) -> Image.Image:
    path = SOURCE / (
        "scene-01-arrival.png",
        "scene-02-signaling-fusion.png",
        "scene-03-tissue-response.png",
    )[index % 3]
    image = cover(Image.open(path).convert("RGB"), size, (0.42, 0.54, 0.47)[index % 3])
    image = ImageEnhance.Contrast(image).enhance(1.08).convert("RGBA")
    shade = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    for y in range(size[1]):
        alpha = round(80 + 145 * (y / size[1]))
        draw.line((0, y, size[0], y), fill=(8, 3, 7, alpha))
    return Image.alpha_composite(image, shade)


def card(
    index: int,
    size: tuple[int, int],
    eyebrow: str,
    headline: str,
    detail: str,
    output: Path,
    language: str = "ko",
):
    image = background(index, size)
    draw = ImageDraw.Draw(image)
    width, height = size
    pad = round(width * 0.055)
    is_landscape = width / height > 1.5
    panel_bottom = 330 if is_landscape else round(height * 0.42)
    draw.rounded_rectangle(
        (pad, pad, width - pad, panel_bottom),
        radius=round(width * 0.018),
        fill=(7, 3, 7, 205),
        outline=(255, 255, 255, 38),
        width=2,
    )
    draw.text((pad + 28, pad + 24), eyebrow, font=font(round(width * 0.017), True), fill=CORAL)
    if is_landscape:
        headline_size = 52 if language == "ko" else 42
    else:
        headline_size = round(width * (0.051 if language == "ko" else 0.041))
    draw.multiline_text(
        (pad + 28, pad + 68),
        headline,
        font=font(headline_size, True),
        fill=IVORY,
        spacing=round(headline_size * 0.2),
    )
    draw.text(
        (pad + 30, panel_bottom - (46 if is_landscape else round(width * 0.05))),
        detail,
        font=font(round(width * 0.018)),
        fill=(226, 211, 202),
    )
    draw.ellipse(
        (pad, height - 82, pad + 15, height - 67),
        fill=AMBER,
    )
    draw.text(
        (pad + 27, height - 91),
        "Science to Message, Beauty to Experience.",
        font=font(round(width * 0.014)),
        fill=IVORY,
    )
    draw.text(
        (width - pad - 72, height - 91),
        "bbbb",
        font=font(round(width * 0.015), True),
        fill=IVORY,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=95, optimize=True)


def render_instagram():
    ig = OUT / "instagram"
    card(
        0,
        (1080, 1350),
        "01 / INSIGHT",
        "보여주는 순서가\n기술의 가치를 만듭니다.",
        "구조보다 먼저 변화의 흐름을 설계합니다.",
        ig / "01-insight-single.jpg",
    )
    carousel = [
        ("질문이 먼저입니다.", "고객이 무엇을 이해해야 하는지 정의합니다."),
        ("도달을 보여줍니다.", "성분과 세포의 출발점과 경로를 연결합니다."),
        ("반응을 포착합니다.", "결합과 신호 전달의 결정적 순간을 강조합니다."),
        ("의미로 마무리합니다.", "세포의 변화를 브랜드 메시지로 연결합니다."),
    ]
    for index, (headline, detail) in enumerate(carousel, 1):
        card(
            index - 1,
            (1080, 1350),
            f"02 / CAROUSEL / {index:02d}",
            headline,
            detail,
            ig / f"02-carousel-{index:02d}.jpg",
        )
    card(
        1,
        (1080, 1920),
        "04 / IMAGE STORY",
        "지금 가장 설명하기\n어려운 단계는 무엇인가요?",
        "성분의 이동 또는 세포의 반응을 메시지로 알려주세요.",
        ig / "04-image-story.jpg",
    )
    card(
        2,
        (1080, 1350),
        "06 / PORTFOLIO",
        "하나의 과학,\n여섯 개의 경험.",
        "3D/MoA · 필름 · 인터랙션 · 교육 콘텐츠",
        ig / "06-portfolio-showcase.jpg",
    )
    shutil.copy2(
        ROOT
        / "images"
        / "social-formats"
        / "body-cell-motion"
        / "reel"
        / "body-cell-motion-reel-ko-v3.mp4",
        ig / "03-cellular-motion-reel.mp4",
    )
    shutil.copy2(
        ROOT
        / "images"
        / "social-formats"
        / "body-cell-motion"
        / "stories"
        / "body-cell-story-03-v2.mp4",
        ig / "05-process-video-story.mp4",
    )


LINKEDIN_TYPES = [
    {
        "slug": "insight",
        "pillar": "science_communication",
        "ko_head": "정보보다 먼저\n이해의 순서를 설계합니다.",
        "en_head": "Design the sequence\nbefore adding information.",
        "ko_topic": "과학 커뮤니케이션 인사이트",
        "en_topic": "Science communication insight",
        "ko_body": "과학 콘텐츠의 첫 질문은 무엇을 더 보여줄지가 아닙니다. 고객이 어떤 순서로 이해해야 하는지를 정하는 일입니다.\n\n복잡한 메디컬·바이오 기술은 구조, 수치, 전문 용어가 많을수록 정확해 보일 수 있습니다. 그러나 고객은 모든 정보를 동시에 처리하지 않습니다. 먼저 무엇이 변하는지 보고, 그다음 변화가 일어나는 이유를 이해하며, 마지막에 근거를 확인합니다.\n\n▪ 고객이 체감할 변화를 먼저 제시합니다.\n▪ 변화를 만드는 핵심 기전을 한 장면씩 연결합니다.\n▪ 임상과 연구 근거는 판단에 필요한 순간에 보여줍니다.\n\nbbbb.beauty는 연구 자료를 줄이는 대신 이해의 순서를 다시 설계합니다. 정확한 과학이 고객의 기억과 선택으로 이어지려면 정보의 양보다 장면의 순서가 먼저 결정되어야 하기 때문입니다.\n\n현재 귀사의 자료는 연구의 순서와 고객의 이해 순서 중 어느 쪽에 더 가깝나요? 댓글로 알려주시거나 프로젝트 배경을 메시지로 남겨주시면 함께 살펴보겠습니다.\n\n프로젝트 문의: https://jhbropark.github.io/pages/contact.html",
        "en_body": "The first question in scientific content is not what else to show. It is the order in which a customer should understand the technology.\n\nMedical and biotechnology stories often contain structures, numbers, and specialist terminology. More detail can look more accurate, but viewers do not process every layer at once. They first notice what changes, then understand why it changes, and finally examine the evidence that supports the claim.\n\n▪ Begin with the change the audience needs to recognize.\n▪ Connect the mechanism in a sequence of focused scenes.\n▪ Introduce research and clinical evidence at the moment it supports a decision.\n\nbbbb.beauty does not simply reduce technical material. We redesign its order of understanding. Accurate science becomes memorable and useful when the sequence of the visual story is decided before the amount of information.\n\nDoes your current material follow the order of the research or the order of customer understanding? Share your perspective in the comments, or send us the project context for an initial review.\n\nProject inquiry: https://jhbropark.github.io/pages/contact.html",
    },
    {
        "slug": "moa-craft",
        "pillar": "moa_craft",
        "ko_head": "움직임에도\n과학적 근거가 필요합니다.",
        "en_head": "Every movement\nneeds scientific logic.",
        "ko_topic": "3D/MoA 제작 노하우",
        "en_topic": "3D and MoA production craft",
        "ko_body": "3D MoA의 설득력은 화려한 입자 효과가 아니라 움직임의 논리에서 시작됩니다.\n\n성분이 어디에서 출발하는지, 어떤 장벽을 통과하는지, 어느 구조와 결합하는지, 그다음 반응이 어디로 이어지는지를 정의해야 카메라와 애니메이션도 정확한 역할을 갖습니다.\n\n▪ 이동 속도는 실제 작용의 시간축과 메시지의 우선순위를 함께 반영합니다.\n▪ 색은 장식이 아니라 성분과 조직, 활성 상태를 구분하는 정보가 됩니다.\n▪ 확대와 초점 이동은 시청자가 원인과 반응을 놓치지 않도록 안내합니다.\n\nbbbb.beauty는 원본 R&D 자료를 검토한 뒤 구조, 방향성, 시간축, 인과관계를 장면 단위로 설계합니다. 시네마틱한 연출은 과학을 가리는 장식이 아니라 정확한 기전을 더 분명하게 전달하는 도구여야 합니다.\n\n현재 제작하려는 MoA에서 가장 중요한 순간은 도달, 결합, 활성화 중 무엇인가요? 프로젝트 목적과 활용 채널을 메시지로 알려주시면 적합한 장면 구조를 함께 검토하겠습니다.\n\n프로젝트 문의: https://jhbropark.github.io/pages/contact.html",
        "en_body": "The persuasive power of a 3D MoA film begins with the logic of movement, not with decorative particles.\n\nWe need to define where an ingredient begins, which barrier it crosses, what structure it reaches, and how the next response develops. Only then can camera movement and animation carry scientific meaning.\n\n▪ Motion speed reflects both the mechanism and the priority of the message.\n▪ Color functions as information, distinguishing ingredients, tissues, and activation states.\n▪ Magnification and focus guide the viewer from cause to response without losing orientation.\n\nbbbb.beauty reviews the original R&D material before designing structure, direction, time, and causality scene by scene. Cinematic direction should not hide the science. It should make the verified mechanism easier to see and remember.\n\nWhich moment matters most in your MoA story: arrival, binding, or activation? Send us the intended use and project context, and we will review an appropriate scene structure with you.\n\nProject inquiry: https://jhbropark.github.io/pages/contact.html",
    },
    {
        "slug": "industry-solution",
        "pillar": "industry_solution",
        "ko_head": "그래프가 읽히지 않는다면\n경험의 순서를 바꿔야 합니다.",
        "en_head": "When graphs are ignored,\nredesign the experience.",
        "ko_topic": "산업별 문제 해결",
        "en_topic": "Industry problem solving",
        "ko_body": "임상 그래프를 추가했는데도 고객이 기술의 차이를 이해하지 못한다면 데이터가 부족한 것이 아닐 수 있습니다.\n\n상세페이지와 세일즈 자료에서 수치가 먼저 등장하면 고객은 무엇을 비교해야 하는지 알기 전에 해석부터 요구받습니다. 변화의 장면, 작용 원리, 근거의 순서로 정보를 재배치하면 숫자는 더 명확한 의미를 갖습니다.\n\n▪ 먼저 고객이 체감할 변화를 시각적으로 제시합니다.\n▪ 다음으로 변화가 발생하는 핵심 기전을 보여줍니다.\n▪ 마지막으로 임상 결과와 데이터가 그 설명을 지지하게 합니다.\n\nbbbb.beauty는 더마·제약·바이오·의료기기 브랜드의 자료를 채널과 구매 여정에 맞는 비주얼 구조로 번역합니다. 같은 데이터라도 상세페이지, 학회 부스, 바이어 미팅에서는 서로 다른 정보 밀도가 필요합니다.\n\n현재 가장 읽히지 않는 자료가 임상 그래프인지, 작용 기전인지 댓글로 알려주세요. 프로젝트 자료와 공개 범위를 보내주시면 우선순위를 함께 정리하겠습니다.\n\n프로젝트 문의: https://jhbropark.github.io/pages/contact.html",
        "en_body": "If customers still cannot understand the difference after more clinical graphs are added, the problem may not be a lack of data.\n\nWhen numbers appear first in a product page or sales deck, viewers are asked to interpret evidence before they know what they should compare. Reordering the story as change, mechanism, and evidence gives the data a clearer role.\n\n▪ Show the customer-relevant change first.\n▪ Explain the mechanism responsible for that change.\n▪ Let the clinical result support the explanation at the end.\n\nbbbb.beauty translates materials from dermocosmetic, pharmaceutical, biotechnology, and medical-device brands into visual structures suited to the channel and buying journey. The same evidence requires different levels of detail on a product page, at a congress booth, or in a buyer meeting.\n\nWhich material is currently harder to communicate: the clinical graph or the mechanism? Share it in the comments, or send the available material and disclosure boundaries so we can help organize the priorities.\n\nProject inquiry: https://jhbropark.github.io/pages/contact.html",
    },
    {
        "slug": "methodology",
        "pillar": "methodology",
        "ko_head": "좋은 장면은\n검수 이전에 설계됩니다.",
        "en_head": "Strong scenes are designed\nbefore final review.",
        "ko_topic": "프로젝트 과정과 방법론",
        "en_topic": "Project process and methodology",
        "ko_body": "의학적 검수를 마지막 단계의 오탈자 확인으로 생각하면 제작 과정에서 가장 중요한 기회를 놓치게 됩니다.\n\n과학 콘텐츠의 정확성은 스토리보드 이전부터 설계되어야 합니다. 어떤 구조를 반드시 정확히 표현할지, 어떤 반응은 강조할 수 있는지, 어디부터는 해석으로 구분해야 하는지를 초기에 합의하면 크리에이티브의 범위도 더 명확해집니다.\n\n▪ 원본 논문, 특허, R&D 자료와 공개 범위를 확인합니다.\n▪ 타겟과 활용 채널에 따라 설명 깊이를 결정합니다.\n▪ 스토리보드와 애니매틱 단계에서 의학적 검수를 진행합니다.\n▪ 최종 장면과 카피를 RA 및 승인 담당자와 확인합니다.\n\nbbbb.beauty는 검수를 창의성을 제한하는 절차가 아니라 더 정확하고 자신 있는 장면을 만드는 설계 도구로 활용합니다.\n\n현재 프로젝트에서 검수는 어느 단계에 참여하고 있나요? 제작 일정과 내부 승인 구조를 알려주시면 적합한 검수 흐름을 함께 검토하겠습니다.\n\n프로젝트 문의: https://jhbropark.github.io/pages/contact.html",
        "en_body": "Treating medical review as a final proofreading step misses one of the most valuable opportunities in production.\n\nScientific accuracy needs to be designed before the storyboard is complete. Early agreement on which structures must remain exact, which responses can be emphasized, and where interpretation begins creates a clearer and more confident creative range.\n\n▪ Review the original papers, patents, R&D material, and disclosure boundaries.\n▪ Define the depth of explanation for the audience and channel.\n▪ Include scientific review during storyboard and animatic development.\n▪ Confirm final scenes and copy with regulatory and approval stakeholders.\n\nbbbb.beauty uses review as a design tool rather than a late restriction. It helps the team create scenes that are both more accurate and more creatively resolved.\n\nAt which stage does scientific review enter your current production process? Send us the timeline and approval structure, and we can discuss a workflow suited to the project.\n\nProject inquiry: https://jhbropark.github.io/pages/contact.html",
    },
    {
        "slug": "portfolio",
        "pillar": "portfolio",
        "ko_head": "하나의 기술을\n채널마다 다르게 경험시킵니다.",
        "en_head": "One technology.\nDifferent channel experiences.",
        "ko_topic": "서비스와 포트폴리오",
        "en_topic": "Services and portfolio",
        "ko_body": "하나의 과학 콘텐츠를 한 편의 영상으로만 끝낼 필요는 없습니다.\n\n검토된 3D 자산과 스토리 구조를 중심으로 브랜드 필름, 학회 발표, 영업 프레젠테이션, 교육 콘텐츠, AR 경험, SNS 숏폼까지 확장하면 제작 자산의 활용 범위가 넓어집니다.\n\n▪ 3D MoA는 보이지 않는 기전과 작용 순서를 설명합니다.\n▪ 다큐멘터리와 인터뷰는 연구의 진정성과 브랜드 관점을 전달합니다.\n▪ AR과 인터랙티브 콘텐츠는 사용자가 구조를 직접 탐색하게 합니다.\n▪ 교육 모듈과 숏폼은 채널별로 필요한 정보 밀도를 조절합니다.\n\nbbbb.beauty는 처음부터 마스터 자산과 채널별 모듈을 분리해 설계합니다. 콘텐츠를 반복 제작하는 대신 하나의 정확한 과학을 여러 고객 접점에서 일관되게 경험시키기 위해서입니다.\n\n현재 가장 먼저 강화하고 싶은 접점은 학회, 영업, 교육, SNS 중 어디인가요? 활용 계획을 알려주시면 확장 가능한 제작 구조를 함께 살펴보겠습니다.\n\n프로젝트 문의: https://jhbropark.github.io/pages/contact.html",
        "en_body": "A scientific story does not need to end as a single film.\n\nA reviewed 3D asset and narrative structure can support a brand film, congress presentation, sales deck, educational module, AR experience, and social short-form content. This expands the value and consistency of the production investment.\n\n▪ 3D MoA explains invisible mechanisms and the order of action.\n▪ Documentary and interviews communicate research integrity and brand perspective.\n▪ AR and interactive experiences allow users to explore structures directly.\n▪ Educational modules and short-form edits adjust information density for each channel.\n\nbbbb.beauty separates master assets from channel-specific modules at the beginning of the project. The goal is not to reproduce the same content repeatedly, but to let one accurate scientific foundation operate consistently across customer touchpoints.\n\nWhich touchpoint would you strengthen first: congress, sales, education, or social media? Share the intended use and we can review an expandable production structure together.\n\nProject inquiry: https://jhbropark.github.io/pages/contact.html",
    },
    {
        "slug": "philosophy",
        "pillar": "philosophy",
        "ko_head": "기술은 정확하게,\n메시지는 쉽게.",
        "en_head": "Keep the science accurate.\nMake the message clear.",
        "ko_topic": "bbbb.beauty의 관점과 철학",
        "en_topic": "bbbb.beauty perspective and philosophy",
        "ko_body": "과학적 정확성과 아름다운 경험 중 하나를 선택해야 한다고 생각하지 않습니다.\n\n정확성만 남은 콘텐츠는 고객에게 멀게 느껴질 수 있고, 아름다움만 남은 콘텐츠는 기술에 대한 신뢰를 만들기 어렵습니다. 중요한 것은 근거를 훼손하지 않으면서 고객이 이해할 수 있는 장면과 언어를 찾는 일입니다.\n\nScience to Message, Beauty to Experience.\n\n이 문장은 복잡한 기술을 단순하게 포장한다는 뜻이 아닙니다. 연구자가 중요하게 보는 구조와 인과관계를 지키고, 브랜드 담당자가 전달해야 할 가치를 분명히 하며, 고객이 기억할 수 있는 경험으로 연결한다는 원칙입니다.\n\nbbbb.beauty는 과학과 브랜드 사이의 이해의 벽을 허무는 전문 크리에이티브 에이전시를 지향합니다. 기술은 정확하게, 메시지는 쉽게. 그 두 기준이 함께 작동할 때 기술력은 신뢰와 선택의 이유가 됩니다.\n\n귀사의 콘텐츠는 지금 정확성과 경험 중 어느 쪽을 더 보완해야 하나요? 댓글이나 메시지로 현재의 고민을 나눠주시면 함께 살펴보겠습니다.\n\n프로젝트 문의: https://jhbropark.github.io/pages/contact.html",
        "en_body": "We do not believe brands should have to choose between scientific accuracy and a beautiful experience.\n\nContent built only around accuracy can feel distant to customers. Content built only around beauty may struggle to create trust in the technology. The task is to find scenes and language that preserve the evidence while making the meaning understandable.\n\nScience to Message, Beauty to Experience.\n\nThis does not mean simplifying complex technology into a decorative claim. It means protecting the structures and causal relationships that matter to researchers, clarifying the value that brand teams need to communicate, and connecting both to an experience the audience can remember.\n\nbbbb.beauty aims to bridge the gap between science and brand understanding. Keep the technology accurate. Make the message clear. When both principles operate together, technical expertise becomes a reason for trust and choice.\n\nWhich side needs more attention in your current content: accuracy or experience? Share the challenge in the comments or send us the project context for a thoughtful first review.\n\nProject inquiry: https://jhbropark.github.io/pages/contact.html",
    },
]


def render_linkedin():
    li = OUT / "linkedin"
    for index, item in enumerate(LINKEDIN_TYPES):
        card(
            index,
            (1200, 627),
            f"0{index + 1} / {item['slug'].upper()}",
            item["ko_head"],
            item["ko_topic"],
            li / f"{index + 1:02d}-{item['slug']}-ko.jpg",
            "ko",
        )
        card(
            index,
            (1200, 627),
            f"0{index + 1} / {item['slug'].upper()}",
            item["en_head"],
            item["en_topic"],
            li / f"{index + 1:02d}-{item['slug']}-en.jpg",
            "en",
        )


def queue_items():
    now = datetime.now(tz=timezone.utc)
    stamp = now.strftime("%Y%m%d")
    scheduled = now.isoformat()
    ig = json.loads(IG_QUEUE.read_text(encoding="utf-8"))
    li = json.loads(LI_QUEUE.read_text(encoding="utf-8"))
    ig_ids = {item["id"] for item in ig["items"]}
    li_ids = {item["id"] for item in li["items"]}

    instagram = [
        {
            "id": f"post_{stamp}_six_types_01_insight",
            "format": "single_image",
            "topic": "보여주는 순서가 기술의 가치를 만듭니다",
            "image_url": f"{RAW}/images/channel-six-types/instagram/01-insight-single.jpg",
            "caption": "좋은 과학 콘텐츠는 정보를 더하는 일보다 고객이 이해할 순서를 설계하는 일에서 시작합니다.\n\nA 구조부터 설명하기 / B 변화부터 보여주기. 어떤 방식이 더 필요하신가요?\n프로필 문의 링크에서 프로젝트 배경을 남겨주세요.",
            "hashtags": ["#과학커뮤니케이션", "#바이오마케팅", "#메디컬콘텐츠", "#3DMOA", "#bbbbbeauty"],
        },
        {
            "id": f"post_{stamp}_six_types_02_carousel",
            "format": "carousel",
            "topic": "과학을 이해 가능한 장면으로 바꾸는 네 단계",
            "image_urls": [
                f"{RAW}/images/channel-six-types/instagram/02-carousel-{i:02d}.jpg"
                for i in range(1, 5)
            ],
            "caption": "질문, 도달, 반응, 의미. 복잡한 기전도 네 단계로 정리하면 고객은 원인과 결과를 따라갈 수 있습니다.\n\n현재 가장 설명하기 어려운 단계를 댓글로 알려주세요. 저장해 다음 콘텐츠 기획에 활용해 보세요.",
            "hashtags": ["#과학시각화", "#메디컬애니메이션", "#바이오콘텐츠", "#브랜드전략", "#bbbbbeauty"],
        },
        {
            "id": f"post_{stamp}_six_types_03_reel",
            "format": "reel",
            "topic": "세포의 이동과 반응을 움직임으로",
            "video_url": f"{RAW}/images/channel-six-types/instagram/03-cellular-motion-reel.mp4",
            "caption": "성분이 도달하고, 세포가 신호를 주고받고, 조직의 반응으로 이어집니다.\n\n보이지 않는 기술을 기억되는 움직임으로 설계합니다. 프로필 문의 링크에서 활용 목적을 알려주세요.",
            "hashtags": ["#메디컬애니메이션", "#3DMOA", "#과학커뮤니케이션", "#ScientificVisualization", "#bbbbbeauty"],
        },
        {
            "id": f"post_{stamp}_six_types_04_image_story",
            "format": "story",
            "topic": "설명하기 어려운 단계 질문",
            "image_url": f"{RAW}/images/channel-six-types/instagram/04-image-story.jpg",
            "caption": "",
            "hashtags": [],
        },
        {
            "id": f"post_{stamp}_six_types_05_video_story",
            "format": "story",
            "topic": "정확한 자료에서 기억되는 장면으로",
            "video_url": f"{RAW}/images/channel-six-types/instagram/05-process-video-story.mp4",
            "caption": "",
            "hashtags": [],
        },
        {
            "id": f"post_{stamp}_six_types_06_portfolio",
            "format": "single_image",
            "topic": "하나의 과학을 여러 고객 경험으로",
            "image_url": f"{RAW}/images/channel-six-types/instagram/06-portfolio-showcase.jpg",
            "caption": "하나의 검토된 과학 자산은 3D MoA, 브랜드 필름, 학회, 영업, 교육, AR 경험으로 확장될 수 있습니다.\n\n가장 먼저 강화하고 싶은 고객 접점을 프로필 문의 링크에 남겨주세요.",
            "hashtags": ["#3D애니메이션", "#메디컬필름", "#AR콘텐츠", "#바이오마케팅", "#bbbbbeauty"],
        },
    ]
    for item in instagram:
        if item["id"] not in ig_ids:
            item.update(
                {
                    "status": "pending",
                    "pillar_id": "six_type_test",
                    "scheduled_time": scheduled,
                    "created_at": scheduled,
                    "generated_by": "codex-six-channel-types",
                }
            )
            ig["items"].append(item)

    for index, item in enumerate(LINKEDIN_TYPES):
        pair_id = f"linkedin_{stamp}_six_types_{index + 1:02d}_{item['slug']}"
        for language, order in (("ko", 1), ("en", 2)):
            item_id = f"{pair_id}_{language}"
            if item_id in li_ids:
                continue
            is_ko = language == "ko"
            li["items"].append(
                {
                    "id": item_id,
                    "pair_id": pair_id,
                    "language": language,
                    "pair_order": order,
                    "status": "pending",
                    "pillar_id": item["pillar"],
                    "content_type": item["slug"],
                    "topic": item["ko_topic"] if is_ko else item["en_topic"],
                    "commentary": item["ko_body"] if is_ko else item["en_body"],
                    "hashtags": (
                        ["#과학커뮤니케이션", "#메디컬애니메이션", "#바이오마케팅", "#bbbbbeauty"]
                        if is_ko
                        else ["#ScienceCommunication", "#MedicalAnimation", "#BiotechMarketing", "#bbbbbeauty"]
                    ),
                    "image_url": (
                        f"{RAW}/images/channel-six-types/linkedin/"
                        f"{index + 1:02d}-{item['slug']}-{language}.jpg"
                    ),
                    "alt_text": (
                        f"bbbb.beauty {item['ko_topic']} LinkedIn 카드"
                        if is_ko
                        else f"bbbb.beauty {item['en_topic']} LinkedIn card"
                    ),
                    "scheduled_time": scheduled,
                    "created_at": scheduled,
                    "generated_by": "codex-six-channel-types",
                }
            )

    IG_QUEUE.write_text(json.dumps(ig, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LI_QUEUE.write_text(json.dumps(li, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    render_instagram()
    render_linkedin()
    queue_items()
    print(OUT)


if __name__ == "__main__":
    main()
