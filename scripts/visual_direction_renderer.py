#!/usr/bin/env python3
"""Render distinct LinkedIn visual directions for bbbb.beauty."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).parent.parent
W, H = 1200, 627
SOURCES = {
    "insight": ROOT / "images" / "tests" / "scientific-choreography" / "02-translation-source.png",
    "moa-craft": ROOT / "images" / "concepts" / "visual-directions-v3" / "01-hyper-silico-source.png",
    "industry-solution": ROOT / "images" / "concepts" / "visual-directions-v3" / "04-data-minimal-source.png",
    "methodology": ROOT / "images" / "concepts" / "visual-directions-v3" / "02-neo-lab-source.png",
    "portfolio": ROOT / "images" / "replacements" / "body-cell-narrative" / "05-multi-channel-source.png",
    "philosophy": ROOT / "images" / "concepts" / "visual-directions-v3" / "03-micro-cinema-source.png",
}
def _pick_font(candidates: list[str]) -> str | None:
    for p in candidates:
        if Path(p).exists():
            return p
    return None


# 런너(Linux)에 존재하는 폰트를 우선 선택하고, 없으면 Windows 경로로 폴백
SANS = _pick_font([
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "C:/Windows/Fonts/NotoSansKR-VF.ttf",
    "C:/Windows/Fonts/malgun.ttf",
])
SERIF = _pick_font([
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
    "C:/Windows/Fonts/NotoSerifKR-VF.ttf",
]) or SANS
LATIN = _pick_font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/bahnschrift.ttf",
]) or SANS


def _font(size: int, *, serif: bool = False, latin: bool = False) -> ImageFont.FreeTypeFont:
    chosen = LATIN if latin else SERIF if serif else SANS
    for path in (chosen, SANS, SERIF, LATIN):
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def _cover(path: Path, size: tuple[int, int], bias_x: float = 0.5, bias_y: float = 0.5) -> Image.Image:
    image = Image.open(path).convert("RGB")
    ratio = max(size[0] / image.width, size[1] / image.height)
    image = image.resize(
        (round(image.width * ratio), round(image.height * ratio)),
        Image.Resampling.LANCZOS,
    )
    left = round((image.width - size[0]) * bias_x)
    top = round((image.height - size[1]) * bias_y)
    return image.crop((left, top, left + size[0], top + size[1]))


def _fit_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_lines: int,
    start_size: int,
    *,
    serif: bool = False,
    latin: bool = False,
) -> tuple[list[str], ImageFont.FreeTypeFont]:
    words = text.replace("\n", " \n ").split()
    lines: list[str] = []
    current_font = _font(start_size, serif=serif, latin=latin)
    for size in range(start_size, 27, -2):
        current_font = _font(size, serif=serif, latin=latin)
        lines = []
        line = ""
        for word in words:
            if word == "\n":
                if line:
                    lines.append(line)
                    line = ""
                continue
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=current_font) <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if len(lines) <= max_lines:
            return lines, current_font
    return lines[:max_lines], current_font


def _brand(draw: ImageDraw.ImageDraw, color: tuple[int, int, int], x: int = 54, y: int = 578) -> None:
    draw.text((x, y), "bbbb.beauty", font=_font(18, latin=True), fill=color)


def _render_insight(headline: str, language: str) -> Image.Image:
    image = Image.new("RGB", (W, H), (239, 235, 226))
    source = _cover(SOURCES["insight"], (700, H), 0.62)
    image.paste(ImageEnhance.Contrast(source).enhance(1.05), (500, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 510, H), fill=(239, 235, 226))
    draw.rectangle((58, 48, 80, 163), fill=(231, 62, 53))
    draw.text((105, 50), "01 / SCIENCE COMMUNICATION", font=_font(18, latin=True), fill=(37, 34, 31))
    lines, title_font = _fit_lines(draw, headline, 370, 4, 57, serif=True, latin=language == "en")
    y = 190
    for line in lines:
        draw.text((58, y), line, font=title_font, fill=(24, 23, 21))
        y += round(title_font.size * 1.24)
    draw.line((58, 515, 445, 515), fill=(37, 34, 31), width=2)
    draw.text((58, 528), "ORDER CREATES UNDERSTANDING", font=_font(16, latin=True), fill=(99, 91, 83))
    _brand(draw, (24, 23, 21))
    return image


def _render_moa(headline: str, language: str) -> Image.Image:
    image = _cover(SOURCES["moa-craft"], (W, H), 0.56, 0.48).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, W, H), fill=(1, 13, 24, 34))
    draw.rectangle((0, 430, W, H), fill=(3, 10, 18, 218))
    draw.rectangle((0, 0, 16, H), fill=(88, 217, 255, 255))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)
    draw.text((52, 43), "02 / MOA CRAFT", font=_font(19, latin=True), fill=(218, 244, 250))
    draw.text((978, 43), "MOTION = EVIDENCE", font=_font(16, latin=True), fill=(218, 244, 250))
    lines, title_font = _fit_lines(draw, headline, 850, 2, 58, latin=language == "en")
    y = 458
    for line in lines:
        draw.text((52, y), line, font=title_font, fill=(248, 246, 239))
        y += round(title_font.size * 1.08)
    _brand(draw, (218, 244, 250), 1015, 582)
    return image.convert("RGB")


def _render_industry(headline: str, language: str) -> Image.Image:
    source = _cover(SOURCES["industry-solution"], (780, H), 0.72)
    image = Image.new("RGB", (W, H), (235, 255, 46))
    image.paste(source, (420, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 450, H), fill=(235, 255, 46))
    for x in range(40, 430, 48):
        draw.line((x, 0, x, H), fill=(180, 194, 35), width=1)
    for y in range(40, H, 48):
        draw.line((0, y, 450, y), fill=(180, 194, 35), width=1)
    draw.text((52, 42), "03 / INDUSTRY SOLUTION", font=_font(18, latin=True), fill=(24, 27, 30))
    lines, title_font = _fit_lines(draw, headline, 335, 4, 53, latin=language == "en")
    y = 170
    for line in lines:
        draw.text((52, y), line, font=title_font, fill=(20, 22, 25))
        y += round(title_font.size * 1.18)
    draw.ellipse((363, 482, 397, 516), fill=(238, 54, 48))
    draw.line((52, 499, 363, 499), fill=(20, 22, 25), width=2)
    draw.text((52, 525), "CHANGE  >  MECHANISM  >  EVIDENCE", font=_font(15, latin=True), fill=(20, 22, 25))
    _brand(draw, (20, 22, 25))
    return image


def _render_methodology(headline: str, language: str) -> Image.Image:
    source = ImageEnhance.Color(_cover(SOURCES["methodology"], (W, H), 0.48)).enhance(0.82)
    image = source.filter(ImageFilter.GaussianBlur(0.35)).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, 520, H), fill=(250, 247, 241, 236))
    draw.rectangle((520, 0, 526, H), fill=(145, 100, 214, 255))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)
    draw.text((56, 45), "04 / METHODOLOGY", font=_font(18, latin=True), fill=(87, 59, 116))
    lines, title_font = _fit_lines(draw, headline, 390, 3, 52, serif=True, latin=language == "en")
    y = 135
    for line in lines:
        draw.text((56, y), line, font=title_font, fill=(32, 29, 34))
        y += round(title_font.size * 1.2)
    for y, (number, label) in zip(
        (404, 442, 480, 518),
        (("01", "SOURCE"), ("02", "STORYBOARD"), ("03", "REVIEW"), ("04", "FINAL")),
    ):
        draw.ellipse((57, y, 75, y + 18), outline=(87, 59, 116), width=2)
        draw.text((90, y - 2), f"{number}  {label}", font=_font(15, latin=True), fill=(73, 66, 77))
    _brand(draw, (32, 29, 34))
    return image.convert("RGB")


def _render_portfolio(headline: str, language: str) -> Image.Image:
    source = _cover(SOURCES["portfolio"], (W, H), 0.5)
    image = Image.new("RGB", (W, H), (12, 10, 10))
    image.paste(source.crop((0, 0, 760, H)), (440, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 455, H), fill=(13, 11, 11))
    draw.rectangle((35, 36, 412, 252), outline=(255, 101, 67), width=3)
    draw.text((55, 55), "05 / PORTFOLIO SYSTEM", font=_font(17, latin=True), fill=(255, 101, 67))
    lines, title_font = _fit_lines(draw, headline, 320, 3, 50, latin=language == "en")
    y = 105
    for line in lines:
        draw.text((55, y), line, font=title_font, fill=(246, 239, 228))
        y += round(title_font.size * 1.1)
    for y, (number, label) in zip(
        (324, 370, 416, 462, 508),
        (("01", "FILM"), ("02", "CONGRESS"), ("03", "SALES"), ("04", "AR"), ("05", "SOCIAL")),
    ):
        draw.text((55, y), number, font=_font(14, latin=True), fill=(255, 101, 67))
        draw.text((104, y - 2), label, font=_font(20, latin=True), fill=(222, 214, 204))
        draw.line((205, y + 9, 392, y + 9), fill=(77, 70, 67), width=1)
    _brand(draw, (246, 239, 228))
    return image


def _render_philosophy(headline: str, language: str) -> Image.Image:
    image = Image.new("RGB", (W, H), (246, 242, 235))
    source = _cover(SOURCES["philosophy"], (H, H), 0.5)
    mask = Image.new("L", (H, H), 0)
    ImageDraw.Draw(mask).ellipse((38, 38, H - 38, H - 38), fill=255)
    image.paste(source, (W - H, 0), mask)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 613, H), fill=(246, 242, 235))
    draw.rectangle((54, 45, 183, 51), fill=(236, 47, 54))
    draw.text((54, 70), "06 / PHILOSOPHY", font=_font(18, latin=True), fill=(38, 34, 32))
    lines, title_font = _fit_lines(draw, headline, 470, 4, 61, serif=True, latin=language == "en")
    y = 175
    for index, line in enumerate(lines):
        color = (236, 47, 54) if index == len(lines) - 1 else (27, 24, 23)
        draw.text((54, y), line, font=title_font, fill=color)
        y += round(title_font.size * 1.2)
    draw.text((54, 501), "SCIENCE TO MESSAGE", font=_font(19, latin=True), fill=(93, 86, 80))
    draw.text((54, 532), "BEAUTY TO EXPERIENCE", font=_font(19, latin=True), fill=(93, 86, 80))
    _brand(draw, (27, 24, 23))
    return image


RENDERERS = {
    "insight": _render_insight,
    "moa-craft": _render_moa,
    "industry-solution": _render_industry,
    "methodology": _render_methodology,
    "portfolio": _render_portfolio,
    "philosophy": _render_philosophy,
}


def render_direction(slug: str, headline: str, language: str, output: Path) -> None:
    if slug not in RENDERERS:
        raise ValueError(f"Unknown visual direction: {slug}")
    output.parent.mkdir(parents=True, exist_ok=True)
    RENDERERS[slug](headline, language).save(output, quality=95, optimize=True)


def create_contact_sheet(paths: list[Path], output: Path) -> None:
    thumb_w, thumb_h = 600, 314
    sheet = Image.new("RGB", (thumb_w * 2, thumb_h * 3), (225, 222, 216))
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(image, ((index % 2) * thumb_w, (index // 2) * thumb_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94, optimize=True)
