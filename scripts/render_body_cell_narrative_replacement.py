#!/usr/bin/env python3
"""Render a Korean-first replacement carousel with coherent body-cell visuals."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "images" / "replacements" / "body-cell-narrative"
OUT = SOURCE / "final"
W = H = 1080
WHITE = (247, 243, 238)
BLACK = (7, 6, 8)
CRIMSON = (224, 39, 45)
VIOLET = (150, 76, 219)
AMBER = (255, 160, 48)
GREY = (190, 181, 177)
FONT = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")


def font(size: int, bold=False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def cover(filename):
    image = Image.open(SOURCE / filename).convert("RGB")
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    return image.crop((left, top, left + side, top + side)).resize((W, H))


def gradient(draw, box, start_alpha, end_alpha):
    x1, y1, x2, y2 = box
    for y in range(y1, y2):
        t = (y - y1) / max(1, y2 - y1 - 1)
        alpha = int(start_alpha * (1 - t) + end_alpha * t)
        draw.line((x1, y, x2, y), fill=(*BLACK, alpha))


def page(draw, number, light=False):
    color = BLACK if light else WHITE
    draw.text((55, 45), "bbbb.beauty", font=font(21, True), fill=color)
    draw.text((966, 48), f"{number}", font=font(18, True), fill=CRIMSON)


def save(image, number):
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / f"carousel-{number:02d}.jpg"
    image.convert("RGB").save(output, quality=95, optimize=True)
    return output


def slide_1():
    image = cover("01-visible-movement-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    gradient(draw, (0, 0, 660, H), 238, 25)
    page(draw, 1)
    draw.text(
        (58, 160),
        "눈에 보이지 않는 작용도,\n움직임으로 보여주면\n이해할 수 있습니다.",
        font=font(49, True),
        fill=WHITE,
        spacing=13,
    )
    draw.text(
        (58, 875),
        "인체 안에서 시작되는 세포의 이동을\n하나의 흐름으로 설계합니다.",
        font=font(25, True),
        fill=WHITE,
        spacing=10,
    )
    return Image.alpha_composite(image, overlay)


def slide_2():
    image = cover("02-mechanism-start-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, W, 255), fill=(*BLACK, 205))
    page(draw, 2)
    draw.text(
        (58, 115),
        "설명의 시작점은\n첫 반응이 일어나는 곳입니다.",
        font=font(46, True),
        fill=WHITE,
        spacing=10,
    )
    draw.rectangle((0, 930, W, H), fill=(*BLACK, 205))
    draw.text(
        (58, 956),
        "성분이 어디에 도달하고 무엇을 활성화하는지 보여줍니다.",
        font=font(23, True),
        fill=WHITE,
    )
    return Image.alpha_composite(image, overlay)


def slide_3():
    image = cover("03-cause-path-response-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    gradient(draw, (0, 0, W, 310), 220, 0)
    page(draw, 3)
    draw.text(
        (58, 112),
        "고객이 이해해야 할 것은\n데이터의 양이 아니라\n변화의 흐름입니다.",
        font=font(43, True),
        fill=WHITE,
        spacing=9,
    )
    stages = [("원인", 80), ("이동", 405), ("반응", 760)]
    for label, x in stages:
        draw.ellipse((x, 923, x + 18, 941), fill=AMBER)
        draw.text((x + 30, 908), label, font=font(24, True), fill=WHITE)
    draw.line((97, 932, 435, 932), fill=VIOLET, width=3)
    draw.line((472, 932, 790, 932), fill=VIOLET, width=3)
    return Image.alpha_composite(image, overlay)


def slide_4():
    image = cover("04-cell-fusion-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    page(draw, 4)
    draw.rectangle((0, 0, W, 180), fill=(*BLACK, 175))
    draw.text(
        (58, 92),
        "세포 하나의 움직임이 주변 조직의 반응으로 이어집니다.",
        font=font(35, True),
        fill=WHITE,
    )
    draw.ellipse((448, 392, 655, 599), outline=AMBER, width=4)
    draw.text((680, 480), "세포 간 신호와 융합", font=font(23, True), fill=WHITE)
    draw.line((645, 495, 675, 495), fill=AMBER, width=4)
    draw.rectangle((0, 930, W, H), fill=(*BLACK, 190))
    draw.text(
        (58, 958),
        "한 장면 안에서 세포의 이동과 조직의 변화를 함께 연결합니다.",
        font=font(23, True),
        fill=WHITE,
    )
    return Image.alpha_composite(image, overlay)


def slide_5():
    image = cover("05-multi-channel-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    gradient(draw, (0, 0, W, 300), 235, 0)
    page(draw, 5)
    draw.text(
        (58, 105),
        "하나의 과학적 장면은\n여러 접점에서 다르게 경험됩니다.",
        font=font(43, True),
        fill=WHITE,
        spacing=10,
    )
    labels = ["브랜드 필름", "학회·전시", "바이어 미팅", "교육 콘텐츠"]
    for index, label in enumerate(labels):
        x = 58 + (index % 2) * 310
        y = 875 + (index // 2) * 58
        draw.ellipse((x, y + 7, x + 12, y + 19), fill=CRIMSON)
        draw.text((x + 23, y), label, font=font(20, True), fill=WHITE)
    return Image.alpha_composite(image, overlay)


def slide_6():
    image = cover("06-context-first-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    gradient(draw, (0, 0, 700, H), 252, 70)
    page(draw, 6)
    draw.text(
        (58, 160),
        "귀사의 기술에서\n가장 설명하기 어려운 부분은\n무엇인가요?",
        font=font(49, True),
        fill=WHITE,
        spacing=12,
    )
    draw.text(
        (58, 455),
        "프로젝트의 배경과 활용 목적을 남겨주시면\n"
        "내용을 먼저 살펴본 뒤, 적합한 시각화 방향을\n"
        "함께 검토하겠습니다.",
        font=font(27),
        fill=(225, 216, 211),
        spacing=14,
    )
    draw.line((58, 760, 525, 760), fill=CRIMSON, width=5)
    draw.text(
        (58, 795),
        "Instagram 프로필의 문의 링크에서\n편하신 방식으로 연락하실 수 있습니다.",
        font=font(24, True),
        fill=WHITE,
        spacing=10,
    )
    return Image.alpha_composite(image, overlay)


def contact_sheet(paths):
    sheet = Image.new("RGB", (2160, 3240), BLACK)
    for index, path in enumerate(paths):
        sheet.paste(
            Image.open(path).convert("RGB"),
            ((index % 2) * 1080, (index // 2) * 1080),
        )
    output = OUT / "body-cell-narrative-review.jpg"
    sheet.save(output, quality=93, optimize=True)
    return output


def main():
    slides = [slide_1(), slide_2(), slide_3(), slide_4(), slide_5(), slide_6()]
    paths = [save(slide, index) for index, slide in enumerate(slides, start=1)]
    paths.append(contact_sheet(paths))
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
