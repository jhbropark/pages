#!/usr/bin/env python3
"""Editorial card renderer for bbbb.beauty — 4:5 Instagram (1080x1350).

Every slide has a role, and each role has its own composition. There is no
shared template: a statement slide is type at 180px and nothing else, an
evidence slide is a numeral cropped by the top edge, a vertical slide is set
in 세로쓰기. What is held constant is only the wordmark, a small index and
the palette — enough to read as one deck, not enough to read as one template.

The typesetting matters as much as the layout, so this module does the things
a person does by hand and a generator usually does not:

  * type knocked out of the photograph instead of laid over a legibility scrim
  * emphasis inside a headline — ``순서가 *전부*다`` sets 전부 larger, heavier
    and in the accent, on the same baseline
  * a numeral set behind the headline and partly occluded by it
  * a halftone screen, which is a print artefact rather than a filter
  * margins that differ per role, and one plate knocked off the grid

Three things are measured rather than assumed, because each of them fails
silently otherwise:

  * text width, so a headline can never overflow its box (``fit_font``)
  * Hangul coverage, because the display face carries the common set and not
    all 11,172 syllables (``serif_for``)
  * knockout contrast, because cutting type out of a uniformly dark photograph
    yields an invisible headline (``_knockout_is_legible``)

See docs/editorial-direction.md for the reasoning and the references.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

REPO_ROOT = Path(__file__).parent.parent

W, H = 1080, 1350
MARGIN = 56


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
# Navy and beige are the brand's own (content/topics.json -> visual_identity).
# Clay and amber are the warm pair the reference decks run on, and amber
# already appears as the dot in images/channel-six-types/. Aqua is deliberately
# absent from every surface: a full-bleed aqua gradient is the generic SaaS
# look this direction exists to move away from.

BLACK = (14, 16, 22)
INK = (26, 32, 44)
PAPER = (247, 245, 240)
CHALK = (228, 223, 214)
CLAY = (178, 72, 44)
AMBER = (226, 158, 66)
ROSE = (206, 180, 168)


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

FONT_DIR = REPO_ROOT / "assets" / "fonts"

SERIF_CANDIDATES = [
    str(FONT_DIR / "Hahmlet.ttf"),
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
]
SANS_CANDIDATES = [
    str(FONT_DIR / "Pretendard.ttf"),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]

# Hahmlet carries the KS X 1001 common set — 2,788 of the 11,172 modern Hangul
# syllables. That covers ordinary Korean prose completely (every one of the 613
# distinct syllables across the 35,742 Korean characters already in this repo
# is present), but a rare syllable would otherwise render as an empty box in a
# published post with nothing to warn anyone.
SERIF_FALLBACK = SERIF_CANDIDATES[1:]

FONT_OVERRIDE: dict[str, str] = {}


@lru_cache(maxsize=8)
def _coverage(path: str) -> frozenset[int]:
    """Every code point a font can actually draw."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return frozenset()  # without fontTools, assume the face is fine
    try:
        font = TTFont(path, fontNumber=0, lazy=True)
    except Exception:
        return frozenset()
    points: set[int] = set()
    for table in font["cmap"].tables:
        points |= set(table.cmap.keys())
    font.close()
    return frozenset(points)


def uncovered(text: str, path: str) -> set[str]:
    """Characters in ``text`` that ``path`` has no glyph for."""
    points = _coverage(path)
    if not points:
        return set()
    return {ch for ch in text if ch.strip() and ord(ch) not in points}


def serif_for(text: str) -> str:
    """The display face to set ``text`` in — Hahmlet unless it would tofu."""
    if "serif" in FONT_OVERRIDE:
        return FONT_OVERRIDE["serif"]
    primary = SERIF_CANDIDATES[0]
    if not Path(primary).exists():
        return ""
    missing = uncovered(text.replace("*", ""), primary)
    if not missing:
        return primary
    for path in SERIF_FALLBACK:
        if Path(path).exists() and not uncovered(text, path):
            print(f"editorial_cards: {''.join(sorted(missing))!r} missing from "
                  f"Hahmlet; falling back to {Path(path).name}", file=sys.stderr)
            return path
    # Something still has to be drawn, but it will contain empty boxes, so say
    # so as loudly as possible rather than publishing a card with holes in it.
    print(f"editorial_cards: WARNING {''.join(sorted(missing))!r} has no glyph "
          f"in any installed serif; the card will render tofu. Install "
          f"fonts-noto-cjk or reword the headline.", file=sys.stderr)
    return primary


def _font(size: int, *, serif: bool = False, weight: str = "Regular",
          path: str = "") -> ImageFont.FreeTypeFont:
    key = "serif" if serif else "sans"
    paths = [path] if path else []
    if key in FONT_OVERRIDE:
        paths.append(FONT_OVERRIDE[key])
    paths += SERIF_CANDIDATES if serif else SANS_CANDIDATES
    for candidate in paths:
        if not Path(candidate).exists():
            continue
        try:
            loaded = ImageFont.truetype(candidate, size)
        except OSError:
            continue
        try:
            loaded.set_variation_by_name(weight)
        except (AttributeError, OSError, ValueError):
            pass  # static font, or no such named instance — its own weight stands
        return loaded
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------------------
# Measured text
# ---------------------------------------------------------------------------

_MEASURE = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def text_width(text: str, font: ImageFont.FreeTypeFont) -> float:
    return _MEASURE.textlength(text, font=font)


def runs(text: str) -> list[tuple[str, bool]]:
    """Split ``순서가 *전부*다`` into [(text, emphasised?), ...]."""
    out: list[tuple[str, bool]] = []
    buf, em = "", False
    for ch in text:
        if ch == "*":
            if buf:
                out.append((buf, em))
            buf, em = "", not em
        else:
            buf += ch
    if buf:
        out.append((buf, em))
    return out


def words_of(para: str) -> list[list[tuple[str, bool]]]:
    """Split a paragraph into words, where a word is a list of runs.

    ``순서가 *전부*다`` is two words, not three: 전부 and 다 belong to the same
    word and differ only in emphasis. Treating each run as its own word lets
    the line break between them and inserts a space there, which is how 전부다
    came out as "전부 / 다".
    """
    words: list[list[tuple[str, bool]]] = []
    cur: list[tuple[str, bool]] = []
    for chunk, em in runs(para):
        parts = chunk.split(" ")
        for i, part in enumerate(parts):
            if i:                       # a real space: the previous word ended
                if cur:
                    words.append(cur)
                cur = []
            if part:
                cur.append((part, em))
    if cur:
        words.append(cur)
    return words


def line_width(line, base, emph) -> float:
    return sum(sum(text_width(t, emph if e else base) for t, e in word)
               for word in line) + (len(line) - 1) * text_width(" ", base)


def wrap_runs(text: str, base, emph, max_width: float):
    """Wrap on word boundaries, keeping each run's emphasis.

    A literal newline is a hard break the author asked for, so it ends a line
    regardless of how much room is left. A single word wider than the column
    breaks per character, which is what unspaced Korean needs.
    """
    lines = []
    for para in text.split("\n"):
        cur = []
        for word in words_of(para):
            trial = cur + [word]
            if cur and line_width(trial, base, emph) > max_width:
                lines.append(cur)
                cur = [word]
            else:
                cur = trial
        if cur:
            lines.append(cur)
    # a lone word still too wide for the column
    out = []
    for line in lines:
        if len(line) == 1 and line_width(line, base, emph) > max_width:
            text_only = "".join(t for t, _ in line[0])
            em = line[0][0][1]
            font = emph if em else base
            while text_width(text_only, font) > max_width and len(text_only) > 1:
                cut = len(text_only) - 1
                while cut > 1 and text_width(text_only[:cut], font) > max_width:
                    cut -= 1
                out.append([[(text_only[:cut], em)]])
                text_only = text_only[cut:]
            out.append([[(text_only, em)]])
        else:
            out.append(line)
    return out


def plain(text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    """Wrapped lines of a plain string, spaces preserved between words."""
    return [" ".join("".join(t for t, _ in word) for word in line)
            for line in wrap_runs(text, font, font, max_width)]


# Body copy carries no emphasis, so the two are the same call.
wrap = plain


def fit_font(text: str, max_width: float, max_height: float, *, serif: bool,
             weight: str, start: int, leading: float, floor: int = 28,
             path: str = "", emph_scale: float = 1.0, emph_weight: str = ""):
    """Largest size at which ``text`` fits the box. Never overflows."""
    size = start
    while size > floor:
        base = _font(size, serif=serif, weight=weight, path=path)
        emph = _font(int(size * emph_scale), serif=serif,
                     weight=emph_weight or weight, path=path)
        lines = wrap_runs(text, base, emph, max_width)
        tallest = max(base.size, emph.size)
        if len(lines) * tallest * leading <= max_height:
            return base, emph, lines
        size -= 3
    base = _font(floor, serif=serif, weight=weight, path=path)
    emph = _font(int(floor * emph_scale), serif=serif,
                 weight=emph_weight or weight, path=path)
    return base, emph, wrap_runs(text, base, emph, max_width)


def draw_line(d, line, x, baseline, base, emph, fill, emph_fill):
    """Draw a wrapped line, runs sitting on a shared baseline."""
    for i, word in enumerate(line):
        for t, e in word:
            font = emph if e else base
            ascent = d.textbbox((0, 0), "한", font=font)[3]
            d.text((x, baseline - ascent), t, font=font,
                   fill=emph_fill if e else fill)
            x += text_width(t, font)
        if i < len(line) - 1:
            x += text_width(" ", base)


def tracked(d, text, x, y, font, fill, track=3.4):
    """Letter-spaced caps, drawn per glyph so the tracking is real."""
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += text_width(ch, font) + track
    return x


def vertical(d, text, x, top, font, fill, gap=10):
    """세로쓰기 — a column of Hangul read top to bottom."""
    y = top
    for ch in text:
        if ch in "\n ":
            continue
        box = d.textbbox((0, 0), ch, font=font)
        d.text((x - (box[2] - box[0]) / 2, y), ch, font=font, fill=fill)
        y += (box[3] - box[1]) + gap
    return y


# ---------------------------------------------------------------------------
# Imagery
# ---------------------------------------------------------------------------

IMAGE_DIRS = [
    REPO_ROOT / "images" / "concepts" / "visual-directions-v3",
    REPO_ROOT / "images" / "tests" / "scientific-choreography",
    REPO_ROOT / "images" / "replacements" / "body-cell-narrative",
]


@lru_cache(maxsize=1)
def available_images() -> tuple[Path, ...]:
    """Every source render the brand already owns, in a stable order."""
    found: list[Path] = []
    for directory in IMAGE_DIRS:
        if directory.is_dir():
            found.extend(sorted(directory.glob("*source*.png")))
    return tuple(found)


def resolve_image(name: str, seed: int = 0) -> Path | None:
    """A named image, a repo-relative path, or a deterministic pick."""
    if name:
        direct = REPO_ROOT / name
        if direct.is_file():
            return direct
        for path in available_images():
            if name in path.stem:
                return path
        print(f"editorial_cards: no image matching {name!r}; picking by index",
              file=sys.stderr)
    pool = available_images()
    return pool[seed % len(pool)] if pool else None


def crop(path: Path, size: tuple[int, int], bias_y=0.5, bias_x=0.5) -> Image.Image:
    im = Image.open(path).convert("RGB")
    scale = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((int(im.width * scale) + 1, int(im.height * scale) + 1),
                   Image.LANCZOS)
    x = int((im.width - size[0]) * bias_x)
    y = int((im.height - size[1]) * bias_y)
    return im.crop((x, y, x + size[0], y + size[1]))


def duotone(im, shadow, highlight, contrast=1.5) -> Image.Image:
    """Map luminance onto a two-colour ramp.

    Every image in the deck resolves to the same two brand colours, which is
    what makes a set of generic 3D renders read as art-directed.
    """
    grey = ImageEnhance.Contrast(im.convert("L")).enhance(contrast)
    lut: list[int] = []
    for channel in range(3):
        lut += [int(shadow[channel] +
                    (highlight[channel] - shadow[channel]) * i / 255)
                for i in range(256)]
    return Image.merge("RGB", (grey, grey, grey)).point(lut)


def halftone(im, cell=7, angle=15, fg=BLACK, bg=PAPER) -> Image.Image:
    """A rotated dot screen — a print artefact, not a filter."""
    grey = ImageEnhance.Contrast(im.convert("L")).enhance(1.25)
    out = Image.new("RGB", im.size, bg)
    d = ImageDraw.Draw(out)
    radians = math.radians(angle)
    cos_a, sin_a = math.cos(radians), math.sin(radians)
    diagonal = int(math.hypot(*im.size))
    for v in range(-diagonal // cell, diagonal // cell):
        for u in range(-diagonal // cell, diagonal // cell):
            x = u * cell * cos_a - v * cell * sin_a
            y = u * cell * sin_a + v * cell * cos_a
            if not (0 <= x < im.size[0] and 0 <= y < im.size[1]):
                continue
            radius = (1 - grey.getpixel((int(x), int(y))) / 255) * cell * 0.78
            if radius > 0.35:
                d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fg)
    return out


def grain(im, amount=10, seed=3) -> Image.Image:
    """A little sensor noise. Perfectly clean gradients are a machine tell."""
    rng = random.Random(seed)
    width, height = im.size
    noise = Image.new("L", (max(width // 2, 1), max(height // 2, 1)))
    noise.putdata([128 + rng.randint(-amount, amount)
                   for _ in range(noise.width * noise.height)])
    noise = noise.resize((width, height), Image.BILINEAR)
    return Image.blend(im, Image.merge("RGB", (noise, noise, noise)), 0.06)


def _layer() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """A transparent layer, so alpha actually blends when composited.

    ImageDraw overwrites the alpha channel of an RGBA image instead of
    blending into it, so anything translucent has to be drawn here and
    composited rather than painted straight onto the card.
    """
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


# ---------------------------------------------------------------------------
# Knockout
# ---------------------------------------------------------------------------

def _luminance(rgb) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def _relative_luminance(value: int) -> float:
    """WCAG relative luminance for one 8-bit grey level."""
    channel = value / 255
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def contrast_ratio(a: int, b: int) -> float:
    """The WCAG contrast ratio between two grey levels, 1.0 to 21.0."""
    high, low = sorted((_relative_luminance(a), _relative_luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# WCAG 2.1 puts large text at 3:1. A knockout headline is always large, and it
# is read by the brighter parts of its letterforms rather than by their average,
# so a quarter of the area clearing 3:1 is the bar.
KNOCKOUT_MIN_RATIO = 3.0
KNOCKOUT_MIN_AREA = 0.25


def _levels_under(photo, mask) -> list[int]:
    """The grey levels of ``photo`` where ``mask`` would let it through.

    Sampled at a sixth scale: this decides between two treatments, and a card
    whose verdict turns on a sixth of a pixel is one where either reads.
    """
    small_mask = mask.resize((W // 6, H // 6), Image.BILINEAR)
    small_photo = photo.resize((W // 6, H // 6), Image.BILINEAR).convert("L")
    return [p for p, m in zip(list(small_photo.tobytes()), list(small_mask.tobytes()))
            if m > 140]


def _knockout_is_legible(photo, mask, ground,
                         min_ratio=KNOCKOUT_MIN_RATIO,
                         min_area=KNOCKOUT_MIN_AREA) -> bool:
    """Would type cut out of this photograph actually be readable?

    A knockout is only as legible as the picture behind the letters. Cutting
    type out of a uniformly dark photograph on a dark ground yields an
    invisible headline, and nothing downstream would notice.

    Two things were wrong with the first version, and the 2026-09-21 afternoon
    card needed both fixed to be caught.

    It asked for a gap of 52 grey levels, which is not a legibility threshold at
    all. That card's duotone mapped the photo to a near-flat level 85 against a
    ground of 16 — a gap of 71, comfortably past the bar, and still only 2.55:1,
    under the 3:1 WCAG minimum for large text. A ratio is the measure that says
    whether two tones read apart; a subtraction is not.

    It also took the mean level under the mask, and a knockout is not read by its
    average. The morning card of the same day had a mean of 116 against that same
    ground, but it earned it honestly: 45% of its letter area cleared 3:1. The
    afternoon card's mean of 87 came from a flat wash where 2.7% cleared it. The
    means were 29 apart; the cards were not remotely alike. Asking what fraction
    of the area is actually readable separates them.
    """
    values = _levels_under(photo, mask)
    if not values:
        return True
    ground_level = round(_luminance(ground))
    legible = sum(1 for v in values if contrast_ratio(v, ground_level) >= min_ratio)
    return legible / len(values) >= min_area


def _text_mask(lines, base, emph, x, top, lh, centred=False) -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for i, line in enumerate(lines):
        start = (W - line_width(line, base, emph)) / 2 if centred else x
        draw_line(md, line, start, top + i * lh, base, emph, 255, 255)
    return mask


# ---------------------------------------------------------------------------
# The quiet constants — all that is held across roles
# ---------------------------------------------------------------------------

def chrome(img, slide, on_dark: bool):
    """Wordmark and index. Deliberately not on the same baseline."""
    d = ImageDraw.Draw(img)
    dim = (146, 150, 160) if on_dark else (152, 144, 132)
    font = _font(21, weight="Medium")
    d.text((MARGIN, H - 62), "bbbb.beauty", font=font, fill=dim)
    index = f"{slide.index:02d}"
    d.text((W - MARGIN - text_width(index, font), H - 96), index, font=font, fill=dim)
    return img


@dataclass
class Slide:
    role: str = "statement"
    headline: str = ""
    sub: str = ""
    kicker: str = ""
    stat: str = ""
    stat_note: str = ""
    items: list[str] = field(default_factory=list)
    image: str = ""
    index: int = 1
    total: int = 1


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

def _cover_scrim(slide, photo):
    """Fallback for a cover whose photograph is too dark to knock type out of."""
    veil, vd = _layer()
    for i in range(560):
        vd.line([(0, H - i), (W, H - i)],
                fill=(14, 17, 24, int(215 * (1 - i / 560) ** 1.5)))
    img = Image.alpha_composite(photo.convert("RGBA"), veil).convert("RGB")
    d = ImageDraw.Draw(img)
    face = serif_for(slide.headline)
    base, emph, lines = fit_font(slide.headline, W - MARGIN * 2, 420, serif=True,
                                 weight="Bold", start=100, leading=1.16, path=face)
    lh = int(base.size * 1.14)
    top = H - 200 - len(lines) * lh
    for i, line in enumerate(lines):
        draw_line(d, line, MARGIN, top + i * lh, base, emph, (247, 245, 241), AMBER)
    if slide.kicker:
        tracked(d, slide.kicker.upper(), MARGIN, 70,
                _font(19, weight="SemiBold"), AMBER, 4.2)
    if slide.sub:
        sf = _font(25)
        d.text((MARGIN, H - 178), plain(slide.sub, sf, W - MARGIN * 2)[0],
               font=sf, fill=(196, 186, 176))
    return chrome(img, slide, True)


def r_cover(slide) -> Image.Image:
    """Full-bleed photograph with the headline cut out of it."""
    path = resolve_image(slide.image, slide.index)
    if path is None:
        return r_statement(slide)
    photo = grain(duotone(crop(path, (W, H), bias_y=0.4),
                          (92, 78, 84), (252, 244, 238), 1.9))
    face = serif_for(slide.headline)
    base, emph, lines = fit_font(slide.headline, W - 96, 470, serif=True,
                                 weight="Bold", start=126, leading=1.04, path=face)
    lh = int(base.size * 1.02)
    top = int(H * 0.30)
    mask = _text_mask(lines, base, emph, 48, top, lh)

    if not _knockout_is_legible(photo, mask, BLACK):
        print("editorial_cards: cover photograph too dark for a knockout; "
              "using the scrim treatment instead", file=sys.stderr)
        return _cover_scrim(slide, photo)

    img = Image.new("RGB", (W, H), BLACK)
    img.paste(photo, (0, 0), mask)
    d = ImageDraw.Draw(img)
    if slide.kicker:
        tracked(d, slide.kicker.upper(), MARGIN, 70,
                _font(19, weight="SemiBold"), CLAY, 4.2)
    if slide.sub:
        sf = _font(26)
        for i, line in enumerate(plain(slide.sub, sf, W - MARGIN * 2)):
            d.text((52, top + len(lines) * lh + 46 + i * 38), line,
                   font=sf, fill=(150, 146, 152))
    return chrome(img, slide, True)


def r_statement(slide) -> Image.Image:
    """Type is the whole composition, with the index set behind it."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    face = serif_for(slide.headline)
    base, emph, lines = fit_font(slide.headline, W - 120, 560, serif=True,
                                 weight="Medium", start=132, leading=0.98,
                                 path=face, emph_scale=1.35, emph_weight="Bold")
    lh = int(max(base.size, emph.size) * 0.92)
    top = int(H * 0.46)

    ghost = _font(560, serif=True, weight="Bold", path=serif_for("0123456789"))
    d.text((W - 300, top - 190), f"{slide.index:02d}", font=ghost, fill=CHALK)

    for i, line in enumerate(lines):
        draw_line(d, line, MARGIN, top + i * lh, base, emph, INK, CLAY)

    d.line([(60, top - 150), (192, top - 150)], fill=CLAY, width=7)
    if slide.sub:
        sf = _font(26)
        block = plain(slide.sub, sf, 560)
        for i, line in enumerate(block):
            d.text((MARGIN, H - 210 - (len(block) - i) * 40), line,
                   font=sf, fill=(110, 102, 92))
    return chrome(img, slide, False)


def r_evidence(slide) -> Image.Image:
    """Halftone plate, the figure cropped by the top edge, type flush right."""
    img = Image.new("RGB", (W, H), PAPER)
    path = resolve_image(slide.image, slide.index)
    if path is not None:
        img.paste(halftone(crop(path, (W, 620), bias_y=0.45), cell=7), (0, H - 620))
    d = ImageDraw.Draw(img)

    figure = slide.stat or f"{slide.index:02d}"
    nf = _font(500, serif=True, weight="Bold", path=serif_for(figure))
    box = d.textbbox((0, 0), figure, font=nf)
    d.text((44, -110), figure, font=nf, fill=CLAY)
    if slide.stat_note:
        d.text((44 + (box[2] - box[0]) + 26, 318), slide.stat_note,
               font=_font(34, weight="SemiBold"), fill=INK)
    if slide.kicker:
        tracked(d, slide.kicker.upper(), W - MARGIN - 150, 70,
                _font(19, weight="SemiBold"), CLAY, 4.2)
    if slide.sub:
        bf = _font(27)
        for i, line in enumerate(plain(slide.sub, bf, 520)):
            d.text((W - MARGIN - text_width(line, bf), 560 + i * 42), line,
                   font=bf, fill=(96, 88, 80))
    return chrome(img, slide, False)


def r_vertical(slide) -> Image.Image:
    """세로쓰기 over a full-bleed duotone."""
    path = resolve_image(slide.image, slide.index)
    if path is None:
        return r_statement(slide)
    img = grain(duotone(crop(path, (W, H)), BLACK, CLAY, 1.6))
    d = ImageDraw.Draw(img)
    face = serif_for(slide.headline)
    columns = [c for c in slide.headline.replace("*", "").split("\n") if c.strip()]
    size = 88
    while size > 44:
        font = _font(size, serif=True, weight="Bold", path=face)
        tallest = max(sum(d.textbbox((0, 0), ch, font=font)[3] + 10
                          for ch in col.replace(" ", "")) for col in columns)
        if tallest <= H - 420 and len(columns) * (size + 40) <= W - 200:
            break
        size -= 4
    font = _font(size, serif=True, weight="Bold", path=face)
    x = W - 150
    for column in columns:                      # columns run right to left
        vertical(d, column, x, 150, font, (244, 240, 236))
        x -= size + 40
    if slide.kicker:
        tracked(d, slide.kicker.upper(), MARGIN + 4, 70,
                _font(19, weight="SemiBold"), AMBER, 4.2)
    if slide.sub:
        sf = _font(25)
        for i, line in enumerate(plain(slide.sub, sf, 600)):
            d.text((60, H - 210 + i * 36), line, font=sf, fill=(206, 190, 182))
    return chrome(img, slide, True)


def r_detail(slide) -> Image.Image:
    """A plate knocked 2° off the grid, the list in the right-hand column."""
    img = Image.new("RGB", (W, H), CHALK)
    path = resolve_image(slide.image, slide.index)
    if path is not None:
        plate = grain(duotone(crop(path, (286, 360)), BLACK, ROSE, 1.5), seed=17)
        img.paste(plate.rotate(-2.2, expand=True, resample=Image.BICUBIC,
                               fillcolor=CHALK), (52, 150))
    d = ImageDraw.Draw(img)

    col = 402
    if slide.kicker:
        tracked(d, slide.kicker.upper(), col, 168, _font(19, weight="SemiBold"),
                CLAY, 3.6)
    face = serif_for(slide.headline)
    base, emph, lines = fit_font(slide.headline, W - col - MARGIN, 260, serif=True,
                                 weight="Medium", start=74, leading=1.22,
                                 path=face, emph_weight="Bold")
    lh = int(base.size * 1.2)
    for i, line in enumerate(lines):
        draw_line(d, line, col, 300 + i * lh, base, emph, INK, CLAY)

    y = 300 + len(lines) * lh + 76
    bf = _font(26)
    nf = _font(30, serif=True, weight="Bold", path=serif_for("0123456789"))
    for i, item in enumerate(slide.items):
        d.text((col, y - 6), f"{i + 1:02d}", font=nf, fill=CLAY)
        block = plain(item, bf, W - col - 108)
        for j, line in enumerate(block):
            d.text((col + 62, y + j * 38), line, font=bf, fill=(58, 52, 44))
        y += 38 * len(block) + 46
    return chrome(img, slide, False)


def r_close(slide) -> Image.Image:
    """Knockout again, centred and small — the one centred card."""
    path = resolve_image(slide.image, slide.index)
    face = serif_for(slide.headline)
    base, emph, lines = fit_font(slide.headline, W - 200, 400, serif=True,
                                 weight="Bold", start=96, leading=1.12, path=face)
    lh = int(base.size * 1.1)
    top = int(H * 0.36)

    photo = None
    if path is not None:
        photo = grain(duotone(crop(path, (W, H), bias_y=0.55),
                              (120, 86, 44), (255, 226, 178), 1.9))
    mask = _text_mask(lines, base, emph, 0, top, lh, centred=True)

    if photo is not None and _knockout_is_legible(photo, mask, BLACK):
        img = Image.new("RGB", (W, H), BLACK)
        img.paste(photo, (0, 0), mask)
    else:
        img = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(img)
        for i, line in enumerate(lines):
            draw_line(d, line, (W - line_width(line, base, emph)) / 2,
                      top + i * lh, base, emph, (246, 244, 240), AMBER)
    d = ImageDraw.Draw(img)

    if slide.sub:
        sf = _font(26)
        for i, line in enumerate(plain(slide.sub, sf, 620)):
            d.text(((W - text_width(line, sf)) / 2,
                    top + len(lines) * lh + 64 + i * 40), line,
                   font=sf, fill=(178, 172, 182))
    tag = "Science to Message, Beauty to Experience."
    tf = _font(20)
    d.text(((W - text_width(tag, tf)) / 2, H - 150), tag, font=tf,
           fill=(112, 108, 120))
    return chrome(img, slide, True)


ROLES = {
    "cover": r_cover,
    "statement": r_statement,
    "evidence": r_evidence,
    "vertical": r_vertical,
    "detail": r_detail,
    "close": r_close,
}


def render(slide: Slide, out: Path) -> Path:
    """Render one card. Unknown roles fall back to a statement."""
    builder = ROLES.get(slide.role)
    if builder is None:
        print(f"editorial_cards: unknown role {slide.role!r}; using statement",
              file=sys.stderr)
        builder = r_statement
    img = builder(slide)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=94, optimize=True)
    return out
