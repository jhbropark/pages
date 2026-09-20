"""Guards for the two defects the editorial card renderer was built to fix.

Both are silent: the old renderer produced a file either way, and the damage
only showed up by eye. A test is the only thing that keeps them fixed.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "editorial_cards.py"
SPEC = importlib.util.spec_from_file_location("editorial_cards", MODULE_PATH)
cards = importlib.util.module_from_spec(SPEC)
# @dataclass resolves annotations through sys.modules, so the module has to be
# registered before it executes.
sys.modules["editorial_cards"] = cards
SPEC.loader.exec_module(cards)


class TextNeverOverflows(unittest.TestCase):
    """The old wrapper split on character count and never measured anything."""

    def setUp(self):
        self.font = cards._font(90, serif=True, weight="Bold")
        self.max_width = 700

    def test_spaced_text_wraps_within_the_box(self):
        text = "연구 순서가 아니라 고객의 이해 순서로 다시 씁니다"
        for line in cards.wrap(text, self.font, self.max_width):
            self.assertLessEqual(cards.text_width(line, self.font), self.max_width)

    def test_unspaced_korean_breaks_per_character(self):
        # A run with no spaces to break on: the old midpoint split produced one
        # line of half the string, however wide that happened to be.
        text = "기술설명이아니라이해설계에서시작됩니다전부한덩어리로"
        lines = cards.wrap(text, self.font, self.max_width)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(cards.text_width(line, self.font), self.max_width)
        self.assertEqual("".join(lines), text)

    def test_explicit_line_breaks_are_kept(self):
        lines = cards.wrap("위\n아래", self.font, self.max_width)
        self.assertEqual(lines, ["위", "아래"])

    def test_fit_font_shrinks_until_the_headline_fits(self):
        long_headline = "고객이 이해하는 순서로 다시 쓰는 과학 커뮤니케이션 설계의 원칙"
        base, emph, lines = cards.fit_font(
            long_headline, 700, 300, serif=True, weight="Bold",
            start=112, leading=1.16,
        )
        self.assertLessEqual(len(lines) * max(base.size, emph.size) * 1.16, 300)
        for line in lines:
            self.assertLessEqual(cards.line_width(line, base, emph), 700)


class AlphaActuallyBlends(unittest.TestCase):
    """ImageDraw writes alpha into an RGBA image instead of blending it.

    The previous card asked for a panel at alpha 218 and got a fully opaque
    one — its interior pixels read exactly the fill colour, so the gradient
    underneath was invisible. Anything translucent has to go through its own
    layer and Image.alpha_composite.
    """

    def test_drawing_straight_onto_rgba_does_not_blend(self):
        # The bug, pinned: this is what the old renderer did.
        base = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        ImageDraw.Draw(base).rectangle([0, 0, 9, 9], fill=(0, 0, 0, 128))
        self.assertEqual(base.convert("RGB").getpixel((5, 5)), (0, 0, 0))

    def test_compositing_a_layer_does_blend(self):
        base = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        layer = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle([0, 0, 9, 9], fill=(0, 0, 0, 128))
        blended = Image.alpha_composite(base, layer).convert("RGB")
        for channel in blended.getpixel((5, 5)):
            self.assertGreater(channel, 0)
            self.assertLess(channel, 255)

    def test_renderer_uses_a_transparent_layer(self):
        layer, draw = cards._layer()
        self.assertEqual(layer.mode, "RGBA")
        self.assertEqual(layer.getpixel((0, 0)), (0, 0, 0, 0))
        self.assertIsInstance(draw, ImageDraw.ImageDraw)


class RenderedCards(unittest.TestCase):
    def test_card_is_four_by_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = cards.render(
                cards.Slide(role="statement", headline="이해 순서로", kicker="원칙"),
                Path(tmp) / "card.jpg",
            )
            self.assertEqual(Image.open(out).size, (1080, 1350))

    def test_every_role_renders_at_the_right_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, role in enumerate(cards.ROLES):
                out = cards.render(
                    cards.Slide(
                        role=role, headline="변화 · 기전 *· 의미*", kicker="원칙",
                        stat="3배", stat_note="더 빨랐습니다", sub="짧은 방주",
                        items=["하나 — 측정된 변화만.", "둘 — 기전을 한 문장으로."],
                        index=i + 1, total=len(cards.ROLES),
                    ),
                    Path(tmp) / f"{role}.jpg",
                )
                self.assertEqual(Image.open(out).size, (1080, 1350), role)

    def test_an_unknown_role_falls_back_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = cards.render(
                cards.Slide(role="does-not-exist", headline="폴백"),
                Path(tmp) / "fallback.jpg",
            )
            self.assertEqual(Image.open(out).size, (1080, 1350))


class Emphasis(unittest.TestCase):
    """``순서가 *전부*다`` sets 전부 differently without breaking the word."""

    def setUp(self):
        self.base = cards._font(120, serif=True, weight="Medium")
        self.emph = cards._font(160, serif=True, weight="Bold")

    def test_runs_are_split_on_the_marker(self):
        self.assertEqual(cards.runs("순서가 *전부*다"),
                         [("순서가 ", False), ("전부", True), ("다", False)])

    def test_emphasis_does_not_create_a_word_boundary(self):
        # The earlier bug: 전부 and 다 were treated as separate words, so the
        # line could break between them and a space was inserted.
        words = cards.words_of("순서가 *전부*다")
        self.assertEqual(len(words), 2)
        self.assertEqual("".join(t for t, _ in words[1]), "전부다")

    def test_the_emphasised_word_stays_whole_when_wrapped(self):
        # Narrow enough to force a break: it must fall before 전부다, never
        # inside it.
        lines = cards.wrap_runs("순서가 *전부*다", self.base, self.emph, 420)
        rendered = ["".join(t for word in line for t, _ in word) for line in lines]
        self.assertGreater(len(rendered), 1)
        self.assertTrue(any("전부다" in line for line in rendered), rendered)
        self.assertFalse(any(line.endswith("전부") for line in rendered), rendered)


class KnockoutLegibility(unittest.TestCase):
    """Type cut out of a picture is only as legible as the picture."""

    def setUp(self):
        base = cards._font(120, serif=True, weight="Bold")
        lines = cards.wrap_runs("연구 순서가\n이해 순서로", base, base, 900)
        self.mask = cards._text_mask(lines, base, base, 48, 400, 124)

    def test_a_flat_dark_photograph_is_rejected(self):
        flat = Image.new("RGB", (cards.W, cards.H), (18, 20, 26))
        self.assertFalse(cards._knockout_is_legible(flat, self.mask, cards.BLACK))

    def test_a_bright_photograph_is_accepted(self):
        bright = Image.new("RGB", (cards.W, cards.H), (238, 232, 226))
        self.assertTrue(cards._knockout_is_legible(bright, self.mask, cards.BLACK))

    def test_the_flat_midtone_that_shipped_is_rejected(self):
        """The 2026-09-21 afternoon card, pinned.

        Its duotone mapped the photo to a near-flat level 85 against a ground of
        16. The first guard compared mean levels and asked for a gap of 52; 71
        cleared it, so a headline at 2.55:1 shipped looking like dark grey on
        near-black. Nothing about that card was dark enough to trip a gap test.
        """
        flat = Image.new("RGB", (cards.W, cards.H), (85, 85, 85))
        self.assertGreater(abs(85 - cards._luminance(cards.BLACK)), 52.0)
        self.assertLess(cards.contrast_ratio(85, 16), 3.0)
        self.assertFalse(cards._knockout_is_legible(flat, self.mask, cards.BLACK))

    def test_a_similar_mean_does_not_mean_a_similar_card(self):
        """Both cards of 2026-09-21 had means the old gap test waved through.

        The difference was never the average — it was how much of the letter
        area was actually readable. A flat wash and a photograph can sit 29
        levels apart in the mean and look nothing alike.
        """
        flat = Image.new("RGB", (cards.W, cards.H), (87, 87, 87))
        photo = Image.new("RGB", (cards.W, cards.H), (85, 85, 85))
        photo.paste(Image.new("RGB", (cards.W, cards.H // 2), (194, 194, 194)),
                    (0, 300))
        ground = cards._luminance(cards.BLACK)
        for image in (flat, photo):       # both clear the old 52-level gap
            levels = cards._levels_under(image, self.mask)
            self.assertGreater(abs(sum(levels) / len(levels) - ground), 52.0)
        self.assertFalse(cards._knockout_is_legible(flat, self.mask, cards.BLACK))
        self.assertTrue(cards._knockout_is_legible(photo, self.mask, cards.BLACK))

    def test_a_photograph_carries_the_knockout_on_its_bright_quarter(self):
        # Mostly dark, but a quarter of the frame is bright enough to read —
        # that is what a photographed knockout actually looks like, and the
        # mean would drag it under.
        mixed = Image.new("RGB", (cards.W, cards.H), (70, 70, 70))
        mixed.paste(Image.new("RGB", (cards.W, cards.H // 2), (236, 232, 228)),
                    (0, 300))
        self.assertTrue(cards._knockout_is_legible(mixed, self.mask, cards.BLACK))


class ContrastRatio(unittest.TestCase):
    """Perceived contrast, not a difference in grey levels."""

    def test_black_on_white_is_the_maximum(self):
        self.assertAlmostEqual(cards.contrast_ratio(255, 0), 21.0, places=1)

    def test_a_colour_against_itself_is_one(self):
        self.assertAlmostEqual(cards.contrast_ratio(120, 120), 1.0, places=6)

    def test_it_is_symmetric(self):
        self.assertAlmostEqual(cards.contrast_ratio(30, 200),
                               cards.contrast_ratio(200, 30), places=9)

    def test_a_gap_in_levels_does_not_predict_the_ratio(self):
        """Why a subtraction was never the right test.

        The same 71-level gap is 2.63:1 down in the shadows and 2.18:1 in the
        midtones — neither reaches the 3:1 a large headline needs, and the gap
        alone tells you nothing about which is which.
        """
        for low in (16, 150):
            self.assertLess(cards.contrast_ratio(low + 71, low), 3.0)


class SourceImagery(unittest.TestCase):
    def test_the_brand_renders_are_found(self):
        self.assertGreater(len(cards.available_images()), 0)

    def test_a_missing_name_still_resolves(self):
        # A buffer naming an image that no longer exists must not crash the
        # daily run; it falls back to a deterministic pick.
        self.assertIsNotNone(cards.resolve_image("no-such-image", 2))


class VendoredFonts(unittest.TestCase):
    """Hahmlet for display, Pretendard for text, both from assets/fonts/."""

    def test_both_faces_are_vendored(self):
        for name in ("Hahmlet.ttf", "Pretendard.ttf"):
            self.assertTrue((cards.FONT_DIR / name).exists(), name)

    def test_display_and_text_faces_are_preferred(self):
        self.assertTrue(cards.SERIF_CANDIDATES[0].endswith("Hahmlet.ttf"))
        self.assertTrue(cards.SANS_CANDIDATES[0].endswith("Pretendard.ttf"))

    def test_a_build_needs_no_font_download(self):
        # Both primaries resolve from the repo, so nothing is fetched at build
        # time — the point of vendoring rather than curling them in the workflow.
        self.assertTrue(Path(cards.SERIF_CANDIDATES[0]).exists())
        self.assertTrue(Path(cards.SANS_CANDIDATES[0]).exists())


class HangulCoverage(unittest.TestCase):
    """Hahmlet carries the common set, not all 11,172 syllables.

    Ordinary Korean prose is fully covered, but the gap is real, so it is
    guarded rather than assumed away.
    """

    def test_pretendard_covers_every_modern_syllable(self):
        missing = cards.uncovered(
            "".join(chr(cp) for cp in range(0xAC00, 0xD7A4)),
            cards.SANS_CANDIDATES[0],
        )
        self.assertEqual(missing, set())

    def test_ordinary_korean_sets_in_hahmlet(self):
        for line in ["연구 순서가 아니라 이해 순서로",
                     "변화 · 기전 · 의미",
                     "보이지 않는 것을 보여주는 일",
                     "과학 커뮤니케이션 3배 bbbb.beauty"]:
            self.assertEqual(cards.uncovered(line, cards.SERIF_CANDIDATES[0]), set(), line)

    def test_a_syllable_outside_the_common_set_is_detected(self):
        # 쁢 is a valid modern syllable that Hahmlet does not carry; the guard
        # has to notice rather than let it through as an empty box.
        self.assertEqual(cards.uncovered("쁢", cards.SERIF_CANDIDATES[0]), {"쁢"})

    def test_buffered_copy_is_all_settable(self):
        """Preflight: nothing waiting to be posted can tofu."""
        buffer_file = cards.REPO_ROOT / "content" / "buffer.json"
        if not buffer_file.exists():
            self.skipTest("no buffer")
        buffer = json.loads(buffer_file.read_text(encoding="utf-8"))
        for item in buffer.get("items", []):
            headlines = [item.get("image_headline", "")]
            headlines += [s.get("headline", "") for s in item.get("slides", [])]
            for headline in headlines:
                face = cards.serif_for(headline)
                self.assertEqual(
                    cards.uncovered(headline, face), set(),
                    f"{headline!r} cannot be set in {Path(face).name}",
                )


if __name__ == "__main__":
    unittest.main()
