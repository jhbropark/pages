#!/usr/bin/env python3
"""Render Korean and English landscape cards for a LinkedIn sequence test."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "images" / "social-formats" / "body-cell-motion" / "source"
OUT = ROOT / "images" / "linkedin" / "cellular-sequence"
W, H = 1200, 627
PANEL_W = 400
FONT = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
IVORY = (248, 242, 232)
CORAL = (255, 105, 78)
AMBER = (255, 180, 82)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def crop_panel(source: Image.Image, index: int) -> Image.Image:
    ratio = max(PANEL_W / source.width, H / source.height)
    resized = source.resize(
        (round(source.width * ratio), round(source.height * ratio)),
        Image.Resampling.LANCZOS,
    )
    x_bias = (0.42, 0.54, 0.47)[index]
    left = round(max(0, resized.width - PANEL_W) * x_bias)
    top = round(max(0, resized.height - H) * 0.5)
    panel = resized.crop((left, top, left + PANEL_W, top + H))
    return ImageEnhance.Contrast(panel).enhance(1.08)


def render(language: str) -> Path:
    sources = [
        Image.open(SOURCE / "scene-01-arrival.png").convert("RGB"),
        Image.open(SOURCE / "scene-02-signaling-fusion.png").convert("RGB"),
        Image.open(SOURCE / "scene-03-tissue-response.png").convert("RGB"),
    ]
    image = Image.new("RGB", (W, H))
    for index, source in enumerate(sources):
        image.paste(crop_panel(source, index), (index * PANEL_W, 0))

    image = image.filter(ImageFilter.GaussianBlur(0.25)).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        alpha = round(110 + 80 * (y / H))
        draw.line((0, y, W, y), fill=(8, 3, 7, alpha))
    draw.rectangle((0, 0, W, H), outline=(255, 255, 255, 38), width=2)

    for x in (PANEL_W, PANEL_W * 2):
        draw.line((x, 0, x, H), fill=(255, 255, 255, 45), width=2)

    if language == "ko":
        labels = ("도달", "신호", "반응")
        headline = "기술의 가치는\n변화의 순서에서 보입니다."
        subline = "성분의 이동부터 세포 신호, 조직 반응까지"
        filename = "cellular-sequence-ko.jpg"
    else:
        labels = ("ARRIVAL", "SIGNAL", "RESPONSE")
        headline = "The value of science appears\nin the sequence of change."
        subline = "From ingredient movement to cellular signal and tissue response"
        filename = "cellular-sequence-en.jpg"

    draw.rounded_rectangle(
        (38, 35, 1162, 245),
        radius=20,
        fill=(10, 5, 9, 190),
        outline=(255, 255, 255, 35),
        width=2,
    )
    draw.text((65, 57), "bbbb.beauty  /  CELLULAR SEQUENCE", font=font(17, True), fill=CORAL)
    draw.multiline_text(
        (65, 98),
        headline,
        font=font(39 if language == "ko" else 34, True),
        fill=IVORY,
        spacing=5,
    )
    draw.text((65, 205), subline, font=font(17), fill=(225, 211, 202))

    for index, label in enumerate(labels):
        x = 48 + index * PANEL_W
        draw.ellipse((x, 520, x + 14, 534), fill=AMBER)
        draw.text((x + 25, 507), f"0{index + 1}  {label}", font=font(18, True), fill=IVORY)
        if index < 2:
            draw.line(
                (x + 165, 527, x + 350, 527),
                fill=(255, 180, 82, 155),
                width=2,
            )

    draw.text(
        (48, 581),
        "Science to Message, Beauty to Experience.",
        font=font(15),
        fill=(238, 226, 216),
    )
    draw.text((1083, 581), "bbbb", font=font(15, True), fill=IVORY)

    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / filename
    Image.alpha_composite(image, overlay).convert("RGB").save(
        output, quality=95, optimize=True
    )
    return output


def main():
    for language in ("ko", "en"):
        print(render(language))


if __name__ == "__main__":
    main()
