import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _load_apod_namecode():
    """Load apod_namecode without its heavy runtime deps (requests, PIL), which
    aren't needed to exercise the pure-Python naming logic."""
    stubs = {}
    if "requests" not in sys.modules:
        stubs["requests"] = types.ModuleType("requests")
    if "PIL" not in sys.modules:
        pil = types.ModuleType("PIL")
        for attr in ("Image", "ImageDraw", "ImageFont", "ImageOps"):
            setattr(pil, attr, types.SimpleNamespace())
        stubs["PIL"] = pil
    sys.modules.update(stubs)

    path = Path(__file__).parents[1] / "namecode_grid" / "apod_namecode.py"
    spec = importlib.util.spec_from_file_location("apod_namecode", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


apod = _load_apod_namecode()
derive_name = apod.derive_name


class DeriveNameTests(unittest.TestCase):
    def test_thin_title_uses_phenomenon_word(self):
        # A title too thin for a two-word name falls back to the phenomenon.
        self.assertEqual(derive_name("Eclipse", "some text"), "ECLIPSE")

    def test_descriptive_title_keeps_specific_words_over_generic_phenomenon(self):
        # 'M27: The Dumbbell Nebula' must stay DUMBBELL.NEBULA, not collapse to
        # the generic NEBULA. Specific beats generic.
        self.assertEqual(derive_name("M27: The Dumbbell Nebula", ""), "DUMBBELL.NEBULA")

    def test_passing_mention_in_explanation_does_not_hijack(self):
        # Regression: an Iapetus image was labeled METEOR because the
        # explanation mentioned meteors once, in passing.
        title = "Saturn's Iapetus: Painted Moon"
        expl = ("Why does one hemisphere of Iapetus appear so much darker? "
                "A stray meteor is not the cause of the two-toned surface.")
        self.assertEqual(derive_name(title, expl), "IAPETUS.PAINTED")

    def test_milky_way_not_labeled_comet(self):
        # Regression: 'Dueling Bands over the Atacama Desert' came out COMET
        # from a single 'comet' mention deep in the explanation.
        title = "Dueling Bands over the Atacama Desert"
        expl = ("What are these two bands in the sky? "
                "The band on the left is the central band of our Milky Way. "
                "A comet was once photographed from here.")
        name = derive_name(title, expl)
        self.assertNotEqual(name, "COMET")
        self.assertEqual(name, "DUELING.ATACAMA")

    def test_subject_phenomenon_in_first_sentence_is_kept(self):
        # The good case we must NOT regress: when the phenomenon really is the
        # subject (named up front), pull it from the explanation.
        title = "Young Moon and Bright Planet"
        expl = ("A lunar occultation of Venus graced the evening sky. "
                "The occultation was visible across the hemisphere.")
        self.assertEqual(derive_name(title, expl), "OCCULTATION")

    def test_repeated_phenomenon_is_treated_as_subject(self):
        title = "A Night in the Desert"
        expl = ("The aurora shimmered overhead. Later the aurora brightened "
                "into a green curtain.")
        self.assertEqual(derive_name(title, expl), "AURORA")

    def test_possessive_s_is_not_a_word(self):
        # 'Saturn's Rings' -> the lone 's' must not become part of the name.
        self.assertEqual(derive_name("Saturn's Rings", ""), "SATURN.RINGS")

    def test_empty_title_falls_back(self):
        self.assertEqual(derive_name("", ""), "APOD")


class AstroValueTests(unittest.TestCase):
    def test_scale_words_are_kept(self):
        # '190 million light-years' must not collapse to '190 ly' — the label
        # value is a real measurement, off-by-a-million is not acceptable.
        self.assertEqual(apod.astro_value("some 190 million light-years away"),
                         "190M ly")
        self.assertEqual(apod.astro_value("about 4.2 light-years distant"),
                         "4.2 ly")
        self.assertEqual(apod.astro_value("roughly 150 million km from the Sun"),
                         "150M km")

    def test_magnitude_and_none(self):
        self.assertEqual(apod.astro_value("shining at magnitude -4.2"), "mag -4.2")
        self.assertIsNone(apod.astro_value("no numbers here"))


class CaptionSystemTests(unittest.TestCase):
    def _brief(self, date="2026-07-07", real=True):
        return {"date": date, "apod_title": "A Test Sky", "work_name": "TEST.SKY",
                "value": "mag -4.2" if real else "42.123", "value_is_real": real}

    def test_hook_rotates_daily_never_repeats_consecutively(self):
        hooks = [apod.pick_hook(self._brief(date=f"2026-07-{d:02d}"))
                 for d in range(1, 8)]
        for a, b in zip(hooks, hooks[1:]):
            self.assertNotEqual(a, b)

    def test_hook_is_deterministic_per_date(self):
        b = self._brief()
        self.assertEqual(apod.pick_hook(b), apod.pick_hook(b))

    def test_data_hook_skipped_for_sim_value(self):
        # 2026-07-04 ordinal % 4 == 1 -> the {value} hook; a hash fallback must
        # not be presented as a measurement, so it reverts to the ritual hook.
        b = self._brief(date="2026-07-04", real=False)
        self.assertIn("today's sky, rendered in code", apod.pick_hook(b))
        self.assertNotIn("42.123", apod.pick_hook(b))

    def test_caption_decodes_phenomenon_and_credits_source(self):
        cap = apod.build_caption(
            self._brief(),
            "What are these two bands? The left one is the Milky Way. More text.")
        self.assertIn("What are these two bands?", cap)          # decode line
        self.assertIn("Source: NASA APOD · 2026-07-07 · mag -4.2", cap)
        self.assertIn("Save this sky ✦ send it to someone who looks up.", cap)
        first_line = cap.splitlines()[0]
        self.assertLessEqual(len(first_line), 125)               # front-loaded hook
        self.assertEqual(cap.count("#"), 5)                      # 4 base + 1 topical

    def test_caption_without_explanation_still_valid(self):
        cap = apod.build_caption(self._brief(real=False), "")
        self.assertIn("A Test Sky.", cap)
        self.assertNotIn("· 42.123", cap)  # sim value stays out of the source line


if __name__ == "__main__":
    unittest.main()
