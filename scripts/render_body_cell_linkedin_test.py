#!/usr/bin/env python3
"""Render full-bleed Korean and English LinkedIn cards for the body-cell test."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).parent.parent
SOURCE = (
    ROOT
    / "images"
    / "replacements"
    / "body-cell-narrative"
    / "01-visible-movement-source.png"
)
OUT = ROOT / "images" / "linkedin" / "body-cell-narrative"
W, H = 1200, 627
FONT = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
WHITE = (247, 244, 240)
MUTED = (190, 181, 180)
RED = (238, 54, 59)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def render(language: str):
    source = Image.open(SOURCE).convert("RGB")
    target_ratio = W / H
    source_ratio = source.width / source.height
    if source_ratio < target_ratio:
        crop_h = int(source.width / target_ratio)
        top = (source.height - crop_h) // 2
        source = source.crop((0, top, source.width, top + crop_h))
    else:
        crop_w = int(source.height * target_ratio)
        left = (source.width - crop_w) // 2
        source = source.crop((left, 0, left + crop_w, source.height))
    image = source.resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x in range(0, 760):
        t = x / 759
        alpha = int(250 * (1 - t) + 35 * t)
        draw.line((x, 0, x, H), fill=(5, 4, 6, alpha))
    draw.rectangle((0, 0, W, H), outline=(255, 255, 255, 35), width=2)

    if language == "ko":
        eyebrow = "CELLULAR MOTION / 01"
        headline = "보이지 않는 작용도,\n움직임으로 보여주면\n이해할 수 있습니다."
        detail = "원인에서 이동으로,\n세포의 반응에서 조직의 변화로."
        filename = "body-cell-narrative-ko.jpg"
    else:
        eyebrow = "CELLULAR MOTION / 01"
        headline = "Invisible mechanisms\nbecome understandable\nwhen they move."
        detail = "From cause to movement.\nFrom cellular response to tissue change."
        filename = "body-cell-narrative-en.jpg"

    draw.text((58, 45), "bbbb.beauty", font=font(18, True), fill=WHITE)
    draw.text((58, 95), eyebrow, font=font(16, True), fill=RED)
    draw.line((58, 126, 205, 126), fill=RED, width=3)
    draw.text(
        (58, 165),
        headline,
        font=font(43 if language == "ko" else 39, True),
        fill=WHITE,
        spacing=10,
    )
    draw.text(
        (60, 465),
        detail,
        font=font(21, False),
        fill=MUTED,
        spacing=8,
    )
    draw.text(
        (60, 574),
        "Science to Message, Beauty to Experience.",
        font=font(15, False),
        fill=WHITE,
    )

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
