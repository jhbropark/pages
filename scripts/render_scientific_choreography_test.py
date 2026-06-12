#!/usr/bin/env python3
"""Render an unframed, non-brand-palette scientific editorial carousel."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "images" / "tests" / "scientific-choreography"
OUT = SOURCE / "final"
W = H = 1080
BLACK = (8, 7, 8)
WHITE = (246, 241, 232)
RED = (225, 35, 34)
PURPLE = (117, 65, 194)
YELLOW = (222, 255, 39)
GREY = (105, 101, 98)
SANS = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
SANS_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
SERIF = Path("C:/Windows/Fonts/NotoSerifKR-VF.ttf")


def font(size: int, bold=False, serif=False):
    path = SERIF if serif else (SANS_BOLD if bold else SANS)
    return ImageFont.truetype(str(path), size)


def cover(name):
    image = Image.open(SOURCE / name).convert("RGB")
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    return image.crop((left, top, left + side, top + side)).resize((W, H))


def save(image, number):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"carousel-{number:02d}.jpg"
    image.convert("RGB").save(path, quality=95, optimize=True)
    return path


def slide_1():
    image = cover("01-collision-source.png").convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.text((62, 62), "BBBB / SCIENTIFIC CHOREOGRAPHY", font=font(16, bold=True), fill=WHITE)
    draw.text(
        (62, 170),
        "보이지 않는 것은\n설명보다 먼저\n감각되어야 합니다.",
        font=font(47, serif=True),
        fill=WHITE,
        spacing=12,
    )
    draw.line((62, 980, 330, 980), fill=YELLOW, width=6)
    draw.text((62, 1002), "01  COLLISION", font=font(17, bold=True), fill=WHITE)
    return image


def slide_2():
    source = ImageOps.grayscale(cover("02-translation-source.png"))
    image = ImageOps.colorize(
        source,
        black=(14, 12, 18),
        white=(218, 220, 229),
    ).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.text((70, 65), "02", font=font(18, bold=True), fill=RED)
    draw.text(
        (682, 120),
        "복잡함을\n줄이는 일이\n아닙니다.",
        font=font(46, serif=True),
        fill=WHITE,
        spacing=10,
    )
    draw.text(
        (688, 340),
        "핵심이 움직일 자리를\n만드는 일입니다.",
        font=font(23),
        fill=(211, 205, 199),
        spacing=8,
    )
    draw.ellipse((576, 554, 608, 586), fill=RED)
    draw.text((650, 955), "COMPLEXITY → GESTURE", font=font(17, bold=True), fill=BLACK)
    return image


def slide_3():
    image = Image.new("RGB", (W, H), YELLOW)
    draw = ImageDraw.Draw(image)
    draw.text((62, 55), "03 / A POINT OF VIEW", font=font(17, bold=True), fill=BLACK)
    draw.text(
        (60, 155),
        "과학은\n정확해야 합니다.",
        font=font(75, serif=True),
        fill=BLACK,
        spacing=12,
    )
    draw.text(
        (60, 480),
        "그러나 기억되려면\n장면이 되어야 합니다.",
        font=font(64, bold=True),
        fill=PURPLE,
        spacing=10,
    )
    draw.line((62, 865, 1000, 865), fill=BLACK, width=3)
    draw.text(
        (62, 902),
        "Evidence is the foundation. Experience is the connection.",
        font=font(21),
        fill=BLACK,
    )
    draw.ellipse((900, 60, 1030, 190), outline=RED, width=8)
    return image


def slide_4():
    image = cover("03-response-source.png").convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.text((55, 55), "04 / CAUSE BECOMES RESPONSE", font=font(17, bold=True), fill=WHITE)
    draw.text((64, 180), "원인", font=font(34, serif=True), fill=WHITE)
    draw.text((405, 460), "이동", font=font(34, serif=True), fill=WHITE)
    draw.text((815, 690), "반응", font=font(34, serif=True), fill=WHITE)
    draw.line((120, 230, 350, 415), fill=YELLOW, width=3)
    draw.line((470, 510, 760, 660), fill=YELLOW, width=3)
    draw.text(
        (55, 934),
        "정보를 나열하지 않고,\n변화의 순간을 설계합니다.",
        font=font(30, bold=True),
        fill=WHITE,
        spacing=8,
    )
    return image


def slide_5():
    image = Image.new("RGB", (W, H), (220, 223, 229))
    draw = ImageDraw.Draw(image)
    image_1 = cover("01-collision-source.png").crop((130, 80, 930, 880)).resize((500, 500))
    source_2 = ImageOps.grayscale(cover("02-translation-source.png"))
    source_2 = ImageOps.colorize(source_2, black=(14, 12, 18), white=(218, 220, 229))
    image_2 = source_2.crop((200, 160, 920, 880)).resize((390, 390))
    image.paste(image_1, (35, 85))
    image.paste(image_2, (650, 420))
    draw.rectangle((480, 0, 650, 1080), fill=RED)
    draw.text((510, 70), "05", font=font(18, bold=True), fill=WHITE)
    draw.text(
        (55, 650),
        "하나의 과학.\n서로 다른 만남.",
        font=font(54, serif=True),
        fill=BLACK,
        spacing=10,
    )
    draw.text(
        (55, 830),
        "브랜드 필름 · 학회 · 바이어 미팅\n교육 · 디지털 경험",
        font=font(25),
        fill=GREY,
        spacing=12,
    )
    return image


def slide_6():
    image = Image.new("RGB", (W, H), (216, 219, 226))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 28, H), fill=PURPLE)
    draw.text((70, 55), "AN INVITATION TO CONVERSE", font=font(16, bold=True), fill=RED)
    draw.text(
        (68, 150),
        "아직 설명하기 어려운\n장면이 있으신가요?",
        font=font(62, serif=True),
        fill=BLACK,
        spacing=12,
    )
    draw.text(
        (70, 390),
        "귀사의 기술과 프로젝트 배경을 들려주실 수 있다면,\n"
        "먼저 충분히 이해한 뒤 함께 가능한 시각적 해석을\n"
        "살펴보겠습니다.",
        font=font(29),
        fill=(55, 51, 49),
        spacing=16,
    )
    draw.line((70, 650, 1010, 650), fill=(145, 137, 132), width=2)
    draw.text(
        (70, 700),
        "대화는 프로필 문의 링크 또는 LinkedIn 메시지에서\n"
        "편하신 방식으로 이어가실 수 있습니다.",
        font=font(25),
        fill=(55, 51, 49),
        spacing=14,
    )
    draw.text((70, 965), "bbbb.beauty", font=font(23, bold=True), fill=BLACK)
    draw.text((70, 1008), "Science to Message, Beauty to Experience.", font=font(18), fill=GREY)
    draw.ellipse((850, 825, 1010, 985), fill=RED)
    draw.ellipse((885, 860, 975, 950), fill=PURPLE)
    return image


def contact_sheet(paths):
    sheet = Image.new("RGB", (2160, 3240), (18, 17, 18))
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        sheet.paste(image, ((index % 2) * 1080, (index // 2) * 1080))
    path = OUT / "scientific-choreography-review.jpg"
    sheet.save(path, quality=93, optimize=True)
    return path


def main():
    slides = [slide_1(), slide_2(), slide_3(), slide_4(), slide_5(), slide_6()]
    paths = [save(slide, index) for index, slide in enumerate(slides, start=1)]
    paths.append(contact_sheet(paths))
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
