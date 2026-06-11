#!/usr/bin/env python3
"""Render full-bleed 1200x627 Korean and English LinkedIn cards."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont


ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
NAVY = (8, 20, 38)
BEIGE = (248, 246, 242)
AQUA = (14, 165, 233)

CARDS = [
    ("01", "투명함의 기술", "THE ART OF TRANSPARENCY", "HYPER-SILICO TRANSPARENCY"),
    ("02", "새로운 연구실", "THE NEW LAB", "NEO-LAB AESTHETIC"),
    ("03", "미시 세계의 영화", "CINEMA AT MICRO SCALE", "MICRO-CINEMATOGRAPHY"),
    ("04", "데이터는 더 적게", "LESS DATA, MORE CLARITY", "DATA MINIMALISM UX"),
]


def font(size: int, variation: str = "Regular") -> ImageFont.FreeTypeFont:
    result = ImageFont.truetype(str(FONT_PATH), size=size)
    result.set_variation_by_name(variation)
    return result


def full_bleed(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGB")
    scale = max(1200 / image.width, 627 / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - 1200) // 2
    top = (resized.height - 627) // 2
    cropped = resized.crop((left, top, left + 1200, top + 627))
    return ImageEnhance.Contrast(cropped).enhance(1.025)


def render(
    source: Path,
    number: str,
    title: str,
    style: str,
    language: str,
) -> Path:
    image = full_bleed(source)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        (58, 48, 760, 220),
        radius=22,
        fill=(*NAVY, 224),
        outline=(*BEIGE, 45),
        width=1,
    )
    draw.rounded_rectangle((58, 48, 68, 220), radius=4, fill=(*AQUA, 255))
    title_size = 48 if language == "ko" else 40
    draw.text((100, 78), title, font=font(title_size), fill=(*BEIGE, 255))
    draw.text(
        (102, 164),
        f"{number}  {style}",
        font=font(15, "Light"),
        fill=(125, 211, 252, 235),
    )
    draw.rounded_rectangle(
        (58, 550, 1142, 606),
        radius=18,
        fill=(*NAVY, 220),
        outline=(*BEIGE, 38),
        width=1,
    )
    brand_font = font(19, "Medium")
    brand_width = draw.textlength("bbbb.beauty", font=brand_font)
    draw.text(
        (600 - brand_width / 2, 565),
        "bbbb.beauty",
        font=brand_font,
        fill=(*BEIGE, 255),
    )
    result = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    output = (
        ROOT
        / "images"
        / "linkedin"
        / f"post_20260612_style_{number}_{language}_landscape.jpg"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "JPEG", quality=95, optimize=True, progressive=True)
    return output


def review_sheet(paths: list[Path]) -> Path:
    canvas = Image.new("RGB", (1280, 1480), (6, 14, 27))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (40, 28),
        "bbbb.beauty | LinkedIn Full-Bleed 1200 x 627",
        font=font(28),
        fill=BEIGE,
    )
    for index, path in enumerate(paths):
        preview = Image.open(path).resize((576, 301), Image.Resampling.LANCZOS)
        column = index % 2
        row = index // 2
        x = 40 + column * 620
        y = 90 + row * 340
        canvas.paste(preview, (x, y))
        draw.text((x, y + 308), path.stem, font=font(14), fill=(160, 190, 207))
    output = ROOT / "images" / "linkedin" / "visual-style-landscape-review.jpg"
    canvas.save(output, "JPEG", quality=93, optimize=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs=4, type=Path)
    args = parser.parse_args()
    outputs = []
    for source, card in zip(args.sources, CARDS, strict=True):
        number, korean, english, style = card
        outputs.append(render(source, number, korean, style, "ko"))
        outputs.append(render(source, number, english, style, "en"))
    outputs.append(review_sheet(outputs))
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
