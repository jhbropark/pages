#!/usr/bin/env python3
"""Render bilingual square covers for the scientific trust article."""

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


def render_cover(
    source: Path,
    output: Path,
    title_lines: list[str],
    category: str,
    language: str,
) -> None:
    image = Image.open(source).convert("RGB")
    scale = max(1080 / image.width, 1080 / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - 1080) // 2
    top = (resized.height - 1080) // 2
    image = resized.crop((left, top, left + 1080, top + 1080))
    image = ImageEnhance.Contrast(image).enhance(1.04)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, 1080, 1080), fill=(7, 20, 38, 42))
    draw.rounded_rectangle(
        (84, 82, 996, 398),
        radius=28,
        fill=(7, 20, 38, 224),
        outline=(248, 246, 242, 42),
        width=1,
    )
    draw.rounded_rectangle((84, 82, 96, 398), radius=5, fill=(*AQUA, 255))

    category_font = font(18, "Medium")
    title_font = font(58 if language == "ko" else 48, "Medium")
    brand_font = font(21, "Medium")
    tagline_font = font(17, "Light")

    draw.text((134, 125), category, font=category_font, fill=(125, 211, 252, 255))
    line_height = 82 if language == "ko" else 68
    for index, line in enumerate(title_lines):
        draw.text(
            (130, 190 + index * line_height),
            line,
            font=title_font,
            fill=(*BEIGE, 255),
        )

    draw.rounded_rectangle(
        (84, 948, 996, 1018),
        radius=22,
        fill=(7, 20, 38, 218),
        outline=(248, 246, 242, 34),
        width=1,
    )
    draw.text((124, 970), "bbbb.beauty", font=brand_font, fill=(*BEIGE, 255))
    tagline = "Science to Message, Beauty to Experience."
    tagline_width = draw.textlength(tagline, font=tagline_font)
    draw.text(
        (956 - tagline_width, 973),
        tagline,
        font=tagline_font,
        fill=(201, 221, 231, 235),
    )

    result = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "JPEG", quality=95, optimize=True, progressive=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("korean_source", type=Path)
    parser.add_argument("english_source", type=Path)
    args = parser.parse_args()

    output_dir = ROOT / "images" / "articles"
    korean = output_dir / "scientific-accuracy-customer-trust-ko-instagram.jpg"
    english = output_dir / "scientific-accuracy-customer-trust-en-instagram.jpg"
    render_cover(
        args.korean_source,
        korean,
        ["정확성만으로는", "신뢰를 만들 수 없다"],
        "과학 커뮤니케이션 인사이트",
        "ko",
    )
    render_cover(
        args.english_source,
        english,
        ["ACCURACY ALONE", "DOES NOT BUILD TRUST"],
        "SCIENCE COMMUNICATION INSIGHT",
        "en",
    )
    print(korean)
    print(english)


if __name__ == "__main__":
    main()
