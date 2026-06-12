#!/usr/bin/env python3
"""Render a result-first Instagram carousel inspired by premium science studios."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).parent.parent
SOURCE = (
    ROOT
    / "images"
    / "concepts"
    / "visual-directions-v3"
    / "01-hyper-silico-source.png"
)
OUT = ROOT / "images" / "tests" / "result-first-moa"
W = H = 1080
NAVY = (7, 20, 38)
BEIGE = (248, 246, 242)
AQUA = (14, 165, 233)
MUTED = (161, 183, 202)
FONT = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def source_image():
    image = Image.open(SOURCE).convert("RGB")
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    return image.crop((left, top, left + side, top + side)).resize((W, H))


def save(image, number):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"carousel-{number:02d}.jpg"
    image.convert("RGB").save(path, quality=95, optimize=True)
    return path


def brand(draw, number, dark=True):
    color = BEIGE if dark else NAVY
    draw.text((58, 46), "bbbb.beauty", font=font(22, True), fill=color)
    draw.text((920, 49), f"{number:02d}", font=font(19), fill=AQUA)


def hero():
    image = source_image().convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, W, 132), fill=(*NAVY, 218))
    draw.rectangle((0, 825, W, H), fill=(*NAVY, 205))
    brand(draw, 1)
    draw.text(
        (58, 858),
        "성분을 설명하지 말고,\n이동을 보여주세요.",
        font=font(48, True),
        fill=BEIGE,
        spacing=8,
    )
    draw.text((720, 1003), "3D / MoA VISUAL", font=font(17, True), fill=AQUA)
    return Image.alpha_composite(image, overlay)


def research_input():
    image = Image.new("RGB", (W, H), BEIGE)
    draw = ImageDraw.Draw(image)
    brand(draw, 2, dark=False)
    draw.text((58, 145), "R&D 정보는\n장면이 아닙니다.", font=font(62, True), fill=NAVY, spacing=10)
    draw.text(
        (58, 330),
        "성분명·입자 크기·전달 경로·근거를\n먼저 시각적 우선순위로 번역합니다.",
        font=font(27),
        fill=(73, 88, 105),
        spacing=12,
    )
    labels = [
        ("01", "WHAT CHANGES", "무엇이 변하는가"),
        ("02", "HOW IT MOVES", "어떻게 이동하는가"),
        ("03", "WHY TO TRUST", "왜 믿을 수 있는가"),
    ]
    for index, (number, english, korean) in enumerate(labels):
        y = 535 + index * 145
        draw.rounded_rectangle((58, y, 1022, y + 112), radius=20, fill=(235, 234, 229))
        draw.text((88, y + 29), number, font=font(22, True), fill=AQUA)
        draw.text((165, y + 24), english, font=font(19, True), fill=NAVY)
        draw.text((600, y + 24), korean, font=font(25, True), fill=NAVY)
    return image


def wireframe():
    base = source_image().convert("L")
    edges = base.filter(ImageFilter.FIND_EDGES)
    edges = ImageEnhance.Contrast(edges).enhance(2.3)
    edges = ImageOps.colorize(edges, black=NAVY, white=AQUA).convert("RGBA")
    wash = Image.new("RGBA", (W, H), (*NAVY, 125))
    image = Image.alpha_composite(edges, wash)
    draw = ImageDraw.Draw(image)
    brand(draw, 3)
    draw.rounded_rectangle((58, 690, 750, 995), radius=28, fill=(*NAVY, 225), outline=(*AQUA, 120), width=2)
    draw.text((95, 730), "구조가 먼저입니다.", font=font(52, True), fill=BEIGE)
    draw.text(
        (95, 815),
        "카메라, 이동 경로, 정보의 위계를\n와이어프레임에서 검증합니다.",
        font=font(26),
        fill=MUTED,
        spacing=12,
    )
    draw.text((95, 935), "WIREFRAME → STORYBOARD", font=font(17, True), fill=AQUA)
    return image


def final_render():
    image = source_image().convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    brand(draw, 4)
    draw.rounded_rectangle((55, 75, 430, 185), radius=55, fill=(*NAVY, 205))
    draw.text((105, 108), "FINAL RENDER", font=font(22, True), fill=BEIGE)
    draw.line((780, 810, 1020, 810), fill=(*AQUA, 255), width=4)
    draw.text((780, 835), "REFRACTION", font=font(17, True), fill=BEIGE)
    draw.text((780, 873), "MOTION", font=font(17, True), fill=BEIGE)
    draw.text((780, 911), "FOCAL DEPTH", font=font(17, True), fill=BEIGE)
    draw.rectangle((0, 987, W, H), fill=(*NAVY, 225))
    draw.text((58, 1007), "과학적 정확성 + 시네마틱 재질과 빛", font=font(22, True), fill=BEIGE)
    return Image.alpha_composite(image, overlay)


def applications():
    image = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(image)
    brand(draw, 5)
    draw.text((58, 145), "한 번 만든 3D 자산은\n한 채널에서 끝나지 않습니다.", font=font(54, True), fill=BEIGE, spacing=10)
    draw.text(
        (58, 330),
        "제품 론칭부터 바이어 미팅과 교육까지,\n같은 과학을 목적에 맞게 재편집합니다.",
        font=font(27),
        fill=MUTED,
        spacing=12,
    )
    items = [
        ("LAUNCH", "제품 론칭"),
        ("CONGRESS", "학회·전시"),
        ("SALES", "바이어 미팅"),
        ("EDUCATION", "교육 콘텐츠"),
    ]
    for index, (english, korean) in enumerate(items):
        x = 58 + (index % 2) * 500
        y = 535 + (index // 2) * 185
        draw.rounded_rectangle((x, y, x + 455, y + 145), radius=25, fill=(15, 42, 68), outline=(40, 79, 108), width=2)
        draw.text((x + 32, y + 30), english, font=font(18, True), fill=AQUA)
        draw.text((x + 32, y + 72), korean, font=font(28, True), fill=BEIGE)
    return image


def cta():
    image = Image.new("RGB", (W, H), BEIGE)
    draw = ImageDraw.Draw(image)
    brand(draw, 6, dark=False)
    draw.text((58, 150), "당신의 기술에서\n가장 먼저 보여줘야 할\n한 장면은 무엇인가요?", font=font(56, True), fill=NAVY, spacing=10)
    draw.text((58, 415), "A 성분 전달   B 작용 기전", font=font(28, True), fill=(71, 88, 104))
    draw.rounded_rectangle((58, 585, 1022, 745), radius=34, fill=AQUA)
    draw.text((105, 625), "댓글에 A 또는 B를 남겨주세요.", font=font(34, True), fill=NAVY)
    draw.rounded_rectangle((58, 785, 1022, 945), radius=34, fill=NAVY)
    draw.text((105, 825), "DM 'MOA' → 기술 시각화 진단 질문", font=font(32, True), fill=BEIGE)
    draw.text((58, 1008), "Science to Message, Beauty to Experience.", font=font(19), fill=(71, 88, 104))
    return image


def contact_sheet(paths):
    sheet = Image.new("RGB", (2160, 3240), (225, 224, 220))
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        x = (index % 2) * 1080
        y = (index // 2) * 1080
        sheet.paste(image, (x, y))
    output = OUT / "result-first-review.jpg"
    sheet.save(output, quality=92, optimize=True)
    return output


def main():
    outputs = [
        save(hero(), 1),
        save(research_input(), 2),
        save(wireframe(), 3),
        save(final_render(), 4),
        save(applications(), 5),
        save(cta(), 6),
    ]
    outputs.append(contact_sheet(outputs))
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
