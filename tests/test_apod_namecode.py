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


if __name__ == "__main__":
    unittest.main()
