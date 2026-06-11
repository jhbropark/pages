#!/usr/bin/env python3
"""Render the visual direction cards with Instagram grid-safe typography."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont


ROOT = Path(__file__).resolve().parent.parent
FONT = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
NAVY = (11, 25, 48)
BEIGE = (248, 246, 242)
AQUA = (14, 165, 233)

CARDS = [
    ("01", "투명함의 기술", "HYPER-SILICO TRANSPARENCY"),
    ("02", "새로운 연구실", "NEO-LAB AESTHETIC"),
    ("03", "미시 세계의 영화", "MICRO-CINEMATOGRAPHY"),
    ("04", "데이터는 더 적게", "DATA MINIMALISM UX"),
]

ENGLISH_CARDS = [
    ("01", "THE ART OF TRANSPARENCY", "HYPER-SILICO TRANSPARENCY"),
    ("02", "THE NEW LAB", "NEO-LAB AESTHETIC"),
    ("03", "CINEMA AT MICRO SCALE", "MICRO-CINEMATOGRAPHY"),
    ("04", "LESS DATA, MORE CLARITY", "DATA MINIMALISM UX"),
]


def font(size: int, variation: str = "Regular") -> ImageFont.FreeTypeFont:
    result = ImageFont.truetype(str(FONT), size=size)
    result.set_variation_by_name(variation)
    return result


def draw_tracking_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    tracking: float,
) -> None:
    x, y = position
    for character in text:
        draw.text((x, y), character, font=text_font, fill=fill)
        x += draw.textlength(character, font=text_font) + tracking


def render(
    source: Path,
    number: str,
    title: str,
    english: str,
    *,
    language: str = "ko",
) -> Path:
    image = Image.open(source).convert("RGB").resize((1080, 1080), Image.Resampling.LANCZOS)
    image = ImageEnhance.Contrast(image).enhance(1.025)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Instagram's 3:4 grid preview crops roughly 135 px from each side.
    # Keep all meaningful type inside x=165..915 with additional breathing room.
    panel = (165, 64, 915, 244)
    draw.rounded_rectangle(
        panel,
        radius=22,
        fill=(*NAVY, 218),
        outline=(*BEIGE, 46),
        width=1,
    )
    draw.rounded_rectangle((165, 64, 173, 244), radius=4, fill=(*AQUA, 255))

    title_size = 48 if language == "ko" else 39
    title_font = font(title_size, "Regular")
    meta_font = font(15, "Light")
    brand_font = font(20, "Medium")

    draw.text((204, 92), title, font=title_font, fill=(*BEIGE, 255))
    draw_tracking_text(
        draw,
        (205, 176),
        f"{number}  {english}",
        meta_font,
        (*AQUA, 225),
        1.2,
    )

    footer = (165, 956, 915, 1018)
    draw.rounded_rectangle(
        footer,
        radius=20,
        fill=(*NAVY, 218),
        outline=(*BEIGE, 42),
        width=1,
    )
    brand = "bbbb.beauty"
    brand_width = draw.textlength(brand, font=brand_font)
    draw.text(
        (540 - brand_width / 2, 972),
        brand,
        font=brand_font,
        fill=(*BEIGE, 255),
    )

    result = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    suffix = "_en" if language == "en" else ""
    output = (
        ROOT
        / "images"
        / "revisions"
        / f"post_20260612_style_{number}_v2{suffix}.jpg"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "JPEG", quality=95, optimize=True, progressive=True)
    return output


def contact_sheet(paths: list[Path], filename: str, heading: str) -> Path:
    background = Image.new("RGB", (1710, 1330), (9, 17, 30))
    draw = ImageDraw.Draw(background)
    heading_font = font(30)
    label_font = font(17)
    draw.text((55, 34), heading, font=heading_font, fill=BEIGE)

    for index, path in enumerate(paths):
        source = Image.open(path).convert("RGB")
        row = index // 2
        column = index % 2
        x = 55 + column * 825
        y = 100 + row * 600

        square = source.resize((520, 520), Image.Resampling.LANCZOS)
        background.paste(square, (x, y))
        draw.text((x, y + 530), f"{index + 1:02}  FULL POST", font=label_font, fill=(175, 205, 220))

        grid_crop = source.crop((135, 0, 945, 1080)).resize((270, 360), Image.Resampling.LANCZOS)
        background.paste(grid_crop, (x + 540, y))
        draw.rectangle((x + 540, y, x + 810, y + 360), outline=AQUA, width=2)
        draw.text((x + 540, y + 370), "INSTAGRAM GRID 3:4", font=label_font, fill=(175, 205, 220))

    output = ROOT / "images" / "revisions" / filename
    background.save(output, "JPEG", quality=94, optimize=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs=4, type=Path)
    args = parser.parse_args()
    outputs = [
        render(source, *card)
        for source, card in zip(args.sources, CARDS, strict=True)
    ]
    english_outputs = [
        render(source, *card, language="en")
        for source, card in zip(args.sources, ENGLISH_CARDS, strict=True)
    ]
    review = contact_sheet(
        outputs,
        "visual-style-v2-review.jpg",
        "bbbb.beauty  |  Korean Typography & Grid-Safe Revision",
    )
    english_review = contact_sheet(
        english_outputs,
        "visual-style-v2-en-review.jpg",
        "bbbb.beauty  |  English Typography & Grid-Safe Revision",
    )
    for output in [*outputs, *english_outputs, review, english_review]:
        print(output)


if __name__ == "__main__":
    main()
