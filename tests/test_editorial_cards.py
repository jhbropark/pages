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
        font, lines = cards.fit_font(
            long_headline, 700, 300, serif=True, weight="Bold",
            start=112, leading=1.16,
        )
        self.assertLessEqual(len(lines) * font.size * 1.16, 300)
        for line in lines:
            self.assertLessEqual(cards.text_width(line, font), 700)


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
                cards.Slide(headline="이해 순서로", kicker="원칙", number=1, total=4),
                Path(tmp) / "card.jpg",
            )
            self.assertEqual(Image.open(out).size, (1080, 1350))

    def test_every_ground_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in cards.GROUNDS:
                out = cards.render(
                    cards.Slide(
                        headline="변화 · 기전 · 의미", ground=name, stat="3배",
                        body="한 문장으로 먼저 답한다.", note="짧은 방주",
                        number=2, total=5,
                    ),
                    Path(tmp) / f"{name}.jpg",
                )
                self.assertTrue(out.exists(), name)

    def test_the_rail_sits_at_the_same_height_on_every_slide(self):
        # The continuity device only works if it does not move between slides.
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(1, 5):
                cards.render(
                    cards.Slide(headline="연속", number=index, total=4),
                    Path(tmp) / f"{index}.jpg",
                )
            self.assertEqual(cards.RAIL_Y, int(cards.H * 0.735))


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
