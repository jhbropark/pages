#!/usr/bin/env python3
"""Prepare Korean and English LinkedIn article cover images."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont


ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
BEIGE = (248, 246, 242)
AQUA = (14, 165, 233)


def font(size: int, variation: str = "Regular") -> ImageFont.FreeTypeFont:
    result = ImageFont.truetype(str(FONT_PATH), size=size)
    result.set_variation_by_name(variation)
    return result


def cover_image(
    source: Path,
    output: Path,
    title_lines: list[str],
    category: str,
    language: str,
) -> None:
    image = Image.open(source).convert("RGB")
    scale = max(1920 / image.width, 1080 / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - 1920) // 2
    top = (resized.height - 1080) // 2
    image = resized.crop((left, top, left + 1920, top + 1080))
    image = ImageEnhance.Contrast(image).enhance(1.025)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        (96, 104, 1050, 610),
        radius=34,
        fill=(7, 20, 38, 218),
        outline=(248, 246, 242, 40),
        width=1,
    )
    draw.rounded_rectangle((96, 104, 108, 610), radius=5, fill=(*AQUA, 255))

    title_font = font(72 if language == "ko" else 56, "Regular")
    meta_font = font(22, "Light")
    brand_font = font(24, "Medium")
    draw.text((154, 154), category, font=meta_font, fill=(125, 211, 252, 255))
    for index, line in enumerate(title_lines):
        draw.text(
            (150, 236 + index * 102),
            line,
            font=title_font,
            fill=(*BEIGE, 255),
        )
    draw.text(
        (152, 538),
        "Science to Message, Beauty to Experience.",
        font=brand_font,
        fill=(201, 221, 231, 245),
    )

    draw.rounded_rectangle(
        (96, 950, 530, 1018),
        radius=22,
        fill=(7, 20, 38, 210),
        outline=(248, 246, 242, 35),
        width=1,
    )
    draw.text((138, 968), "bbbb.beauty", font=brand_font, fill=(*BEIGE, 255))

    result = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "JPEG", quality=95, optimize=True, progressive=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("korean_source", type=Path)
    parser.add_argument("english_source", type=Path)
    args = parser.parse_args()

    output_dir = ROOT / "images" / "articles"
    korean = output_dir / "scientific-accuracy-customer-trust-ko-cover.jpg"
    english = output_dir / "scientific-accuracy-customer-trust-en-cover.jpg"
    cover_image(
        args.korean_source,
        korean,
        ["과학적 정확성만으로는", "고객의 신뢰를 만들 수 없다"],
        "MEDICAL & BEAUTY COMMUNICATION",
        "ko",
    )
    cover_image(
        args.english_source,
        english,
        ["WHY SCIENTIFIC ACCURACY", "ALONE DOES NOT BUILD TRUST"],
        "GLOBAL MEDICAL & BEAUTY STRATEGY",
        "en",
    )
    print(korean)
    print(english)


if __name__ == "__main__":
    main()
