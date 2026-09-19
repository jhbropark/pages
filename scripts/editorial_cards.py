#!/usr/bin/env python3
"""Editorial card renderer for bbbb.beauty — 4:5 Instagram (1080x1350).

Replaces the centred navy-panel-on-gradient card that ``generate_content.py``
used to draw. The direction comes from four reference decks the owner chose as
the homage (see ``docs/editorial-direction.md``):

  * a dark cover slide opening onto light interiors, a persistent wordmark and
    a giant ghosted slide number  (REZOLVE.ai carousel)
  * a serif display headline set in tight all-caps over a warm, muted ground,
    with lowercase ``*asterisk`` captions and cut-paper sticker shapes
    (supergut carousel)
  * a continuity rail that runs at the same height on every slide, so a
    carousel reads as one long canvas rather than N separate cards
    (the "Work Smarter" AI carousel)

Everything is measured before it is drawn: no text is placed without asking the
font how wide it is, and every translucent shape is composited onto its own
RGBA layer rather than written straight into the base image (``ImageDraw``
overwrites the alpha channel instead of blending it).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).parent.parent

W, H = 1080, 1350
MARGIN = 84

# The rail sits at a fixed fraction of the height on every slide, which is what
# makes a carousel read as one continuous canvas when you swipe it.
RAIL_Y = int(H * 0.735)

# Reserved right-hand column: the sticker lives here and type never enters it.
STICKER_GUTTER = 150


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
# Deep navy and soft beige are the brand's own (content/topics.json ->
# visual_identity). Aqua is deliberately demoted: it now appears only on data,
# never as the surface of a card, because a full-bleed aqua gradient is exactly
# the generic SaaS look this direction moves away from. Clay and amber are the
# warm pair the reference decks run on, and amber already appears as the dot in
# images/channel-six-types/.

INK = (30, 41, 59)        # #1E293B deep navy
PAPER = (248, 246, 242)   # #F8F6F2 soft beige
ROSE = (217, 198, 189)    # #D9C6BD dusty rose
CLAY = (180, 84, 58)      # #B4543A
AMBER = (224, 162, 78)    # #E0A24E
AQUA = (14, 165, 233)     # #0EA5E9 — data only


@dataclass(frozen=True)
class Ground:
    """One of the three surfaces a slide can sit on."""

    bg: tuple[int, int, int]
    text: tuple[int, int, int]
    muted: tuple[int, int, int]
    accent: tuple[int, int, int]
    ghost: tuple[int, int, int]  # the giant slide number
    rail: tuple[int, int, int]


GROUNDS: dict[str, Ground] = {
    # cover / CTA — dark, the deck's bookends
    "ink": Ground(INK, PAPER, (146, 158, 176), AMBER, (41, 54, 74), (86, 98, 116)),
    # body slides — the default
    "paper": Ground(PAPER, INK, (138, 130, 120), CLAY, (236, 232, 226), (206, 200, 192)),
    # image / quote slides — the warm breath between body slides
    "rose": Ground(ROSE, (58, 44, 38), (128, 108, 100), CLAY, (206, 186, 177), (185, 165, 156)),
}


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

SERIF_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
    str(REPO_ROOT / "assets" / "fonts" / "NotoSerifKR.ttf"),
]
SANS_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    str(REPO_ROOT / "assets" / "fonts" / "NotoSansKR.ttf"),
]

# Set by tests and by the preview build to point at a downloaded copy.
FONT_OVERRIDE: dict[str, str] = {}


def _font(size: int, *, serif: bool = False, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    key = "serif" if serif else "sans"
    paths = [FONT_OVERRIDE[key]] if key in FONT_OVERRIDE else []
    paths += SERIF_CANDIDATES if serif else SANS_CANDIDATES
    for path in paths:
        if not Path(path).exists():
            continue
        try:
            loaded = ImageFont.truetype(path, size)
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


def wrap(text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    """Greedy wrap that asks the font, not the character count.

    Korean wraps per character when a run has no spaces, which is what the old
    ``_wrap_headline`` could not do: it split on the midpoint and hoped.
    """
    if "\n" in text:
        out: list[str] = []
        for para in text.split("\n"):
            out.extend(wrap(para, font, max_width) if para.strip() else [""])
        return out
    if text_width(text, font) <= max_width:
        return [text]
    lines: list[str] = []
    for chunk in text.split():
        if not lines:
            lines.append(chunk)
            continue
        trial = f"{lines[-1]} {chunk}"
        if text_width(trial, font) <= max_width:
            lines[-1] = trial
        else:
            lines.append(chunk)
    # any single run still too wide (a long unspaced Korean phrase) breaks by char
    out: list[str] = []
    for line in lines:
        while text_width(line, font) > max_width and len(line) > 1:
            cut = len(line) - 1
            while cut > 1 and text_width(line[:cut], font) > max_width:
                cut -= 1
            out.append(line[:cut])
            line = line[cut:]
        out.append(line)
    return out


def fit_font(
    text: str,
    max_width: float,
    max_height: float,
    *,
    serif: bool,
    weight: str,
    start: int,
    leading: float,
    floor: int = 28,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Largest size at which ``text`` fits the box. Never overflows."""
    size = start
    while size > floor:
        font = _font(size, serif=serif, weight=weight)
        lines = wrap(text, font, max_width)
        if len(lines) * size * leading <= max_height:
            return font, lines
        size -= 3
    font = _font(floor, serif=serif, weight=weight)
    return font, wrap(text, font, max_width)


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _layer() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """A transparent layer, so alpha actually blends when composited."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def starburst(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r_outer: float,
    color: tuple[int, int, int],
    *,
    points: int = 8,
    ratio: float = 0.46,
    rotation: float = 0.0,
    alpha: int = 255,
) -> None:
    """The cut-paper sticker shape the supergut deck scatters over its grounds."""
    verts = []
    for i in range(points * 2):
        angle = math.radians(rotation + i * 180 / points)
        radius = r_outer if i % 2 == 0 else r_outer * ratio
        verts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(verts, fill=(*color, alpha))


def continuity_rail(draw: ImageDraw.ImageDraw, g: Ground, index: int, total: int) -> None:
    """A hairline at a fixed height with progress ticks — the seamless device.

    The filled portion advances with the slide index, so swiping reads as one
    canvas being traversed rather than a stack of unrelated cards.
    """
    x0, x1 = MARGIN, W - MARGIN
    draw.line([(x0, RAIL_Y), (x1, RAIL_Y)], fill=(*g.rail, 130), width=3)
    if total > 1:
        filled = x0 + (x1 - x0) * (index + 1) / total
        draw.line([(x0, RAIL_Y), (filled, RAIL_Y)], fill=(*g.accent, 255), width=6)
    for i in range(total):
        tx = x0 + (x1 - x0) * i / max(total - 1, 1)
        draw.line([(tx, RAIL_Y - 7), (tx, RAIL_Y + 7)], fill=(*g.rail, 150), width=2)


# ---------------------------------------------------------------------------
# Slide
# ---------------------------------------------------------------------------

@dataclass
class Slide:
    headline: str
    ground: str = "paper"
    kicker: str = ""            # small tracked label above the headline
    note: str = ""              # the "*lowercase aside" caption
    stat: str = ""              # a figure set huge in the accent
    stat_note: str = ""
    body: str = ""              # inverted block, ref2's key-line device
    number: int | None = None
    total: int = 1
    wordmark: str = "bbbb.beauty"


def render(slide: Slide, out: Path) -> Path:
    g = GROUNDS[slide.ground]
    img = Image.new("RGB", (W, H), g.bg)

    # --- giant ghosted slide number, bottom-right, cropped by the edge -----
    if slide.number is not None:
        nf = _font(460, serif=True, weight="Bold")
        label = f"{slide.number:02d}"
        nd = ImageDraw.Draw(img)
        box = nd.textbbox((0, 0), label, font=nf)
        nd.text(
            (W - MARGIN - (box[2] - box[0]) + 26, H - MARGIN - (box[3] - box[1]) - 54),
            label,
            font=nf,
            fill=g.ghost,
        )

    # --- sticker shapes, rotated per slide so no two repeat ---------------
    stick, sd = _layer()
    seed = (slide.number or 0)
    starburst(sd, W - MARGIN - 40, MARGIN + 150 + (seed % 3) * 46, 54, g.accent,
              rotation=seed * 13, alpha=235)
    starburst(sd, MARGIN + 22, H - 190 - (seed % 2) * 60, 30, AMBER if g.bg != INK else CLAY,
              points=6, rotation=seed * 21 + 8, alpha=200)
    img = Image.alpha_composite(img.convert("RGBA"), stick)

    d = ImageDraw.Draw(img)

    # --- persistent wordmark, top-right -----------------------------------
    wf = _font(25, weight="Medium")
    d.text((W - MARGIN - text_width(slide.wordmark, wf), MARGIN - 6),
           slide.wordmark, font=wf, fill=g.muted)

    y = MARGIN - 4

    # --- kicker ------------------------------------------------------------
    if slide.kicker:
        kf = _font(23, weight="Bold")
        tracked = " ".join(slide.kicker.upper())
        d.text((MARGIN, y), tracked, font=kf, fill=g.accent)
    y += 150

    # --- serif display headline, all-caps for Latin, tight leading --------
    # the right-hand gutter is reserved for the sticker, so type never collides
    hf, lines = fit_font(
        slide.headline, W - MARGIN * 2 - STICKER_GUTTER, 470,
        serif=True, weight="Bold", start=112, leading=1.16,
    )
    lh = hf.size * 1.16
    for i, line in enumerate(lines):
        d.text((MARGIN, y + i * lh), line, font=hf, fill=g.text)
    y += len(lines) * lh + 34

    # --- the "*lowercase aside" -------------------------------------------
    if slide.note:
        af = _font(30, weight="Regular")
        for i, line in enumerate(wrap(f"*{slide.note}", af, W - MARGIN * 2 - 160)):
            d.text((MARGIN, y + i * 42), line, font=af, fill=g.muted)
        y += 60

    # --- a figure, set huge in the accent ---------------------------------
    if slide.stat:
        sf = _font(150, serif=True, weight="Bold")
        d.text((MARGIN, y), slide.stat, font=sf, fill=g.accent)
        if slide.stat_note:
            nf2 = _font(27, weight="Medium")
            d.text((MARGIN + text_width(slide.stat, sf) + 26, y + 104),
                   slide.stat_note, font=nf2, fill=g.muted)
        y += 185

    # --- inverted block for the key line ----------------------------------
    if slide.body:
        bf = _font(31, weight="Regular")
        blines = wrap(slide.body, bf, W - MARGIN * 2 - 88)
        bh = len(blines) * 46 + 52
        top = min(y + 8, RAIL_Y - bh - 30)
        inv, idraw = _layer()
        idraw.rectangle([MARGIN, top, W - MARGIN, top + bh], fill=(*g.text, 255))
        img = Image.alpha_composite(img, inv)
        d = ImageDraw.Draw(img)
        for i, line in enumerate(blines):
            d.text((MARGIN + 34, top + 26 + i * 46), line, font=bf, fill=g.bg)

    # --- rail, composited so its alpha blends ------------------------------
    rail, rdraw = _layer()
    continuity_rail(rdraw, g, (slide.number or 1) - 1, max(slide.total, 1))
    img = Image.alpha_composite(img, rail)
    d = ImageDraw.Draw(img)

    # --- footer ------------------------------------------------------------
    if slide.ground == "ink":
        ff = _font(24, weight="Medium")
        d.text((MARGIN, H - MARGIN - 26), "Science to Message, Beauty to Experience.",
               font=ff, fill=g.muted)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=94, optimize=True)
    return out
