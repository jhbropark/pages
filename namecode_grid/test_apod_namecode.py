"""What the APOD namecode generator is allowed to claim.

The module imports requests / Pillow / krea at import time. krea is a sibling
script that talks to a paid API, so it is always stubbed; requests and Pillow
are stubbed only when they are not installed. Nothing here touches the network,
the repo, or the Krea account.

    python -m unittest test_apod_namecode -v
"""

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)
    return sys.modules[name]


def _install_stubs():
    """krea always; requests / PIL only if genuinely absent."""
    _stub("krea",
          submit=lambda *a, **k: (_ for _ in ()).throw(AssertionError("krea.submit called")),
          wait=lambda *a, **k: (_ for _ in ()).throw(AssertionError("krea.wait called")))
    if importlib.util.find_spec("requests") is None:
        class _RequestException(Exception):
            pass

        class _HTTPError(_RequestException):
            def __init__(self, *a, **k):
                super().__init__(*a)

        _stub("requests", get=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("network call in a unit test")),
            RequestException=_RequestException, HTTPError=_HTTPError)
    if importlib.util.find_spec("PIL") is None:
        pil = _stub("PIL")
        for attr in ("Image", "ImageDraw", "ImageFont", "ImageOps"):
            setattr(pil, attr, types.SimpleNamespace())
            sys.modules[f"PIL.{attr}"] = getattr(pil, attr)


def _load():
    _install_stubs()
    spec = importlib.util.spec_from_file_location(
        "apod_namecode_under_test", HERE / "apod_namecode.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


apod = _load()


COMET_ASIDE = ("The field was imaged over several nights. A comet drifted "
               "through the same patch of sky that week, and the galaxy "
               "behind it is a further 12 million light-years away.")


def sample_brief(**over):
    brief = {
        "date": "2026-09-24",
        "apod_title": "The Ghosts of Five Supernovas",
        "work_name": "SUPERNOVA",
        "label": "namecode - SUPERNOVA | 200 hr",
        "source": "https://apod.nasa.gov/apod/image/2609/5SNR_Auriga_2000.jpg",
        "prompt": "…",
        "apod_url": "https://apod.nasa.gov/apod/ap260924.html",
        "explanation": "The ghosts of five supernovas haunt this image.",
    }
    brief.update(over)
    return brief


class TheTitleDecidesTheName(unittest.TestCase):
    """The regression this patch exists for: a phenomenon mentioned in passing
    three sentences into the explanation used to outrank the actual subject."""

    def test_a_nebula_stays_a_nebula_when_the_text_mentions_a_comet(self):
        self.assertEqual(
            apod.derive_name("The Cocoon Nebula Wide Field", COMET_ASIDE), "NEBULA")

    def test_a_lunar_crater_stays_a_crater_when_the_text_mentions_a_comet(self):
        self.assertEqual(
            apod.derive_name("Tycho: A Lunar Crater", COMET_ASIDE), "CRATER")

    def test_a_comet_in_the_title_is_still_a_comet(self):
        self.assertEqual(apod.derive_name("Comet Tsuchinshan-ATLAS over Chile"), "COMET")

    def test_specific_beats_generic_inside_one_title(self):
        self.assertEqual(apod.derive_name("A Lunar Eclipse over Seoul"), "ECLIPSE")
        self.assertEqual(apod.derive_name("Solar Prominence Rising"), "PROMINENCE")

    def test_a_generic_body_wins_only_when_nothing_sharper_is_there(self):
        self.assertEqual(apod.derive_name("The Lunar Farside"), "LUNAR")


class NamesThePatchAdds(unittest.TestCase):
    def test_sensible_title_recognition(self):
        for title, expected in [
            ("Zodiacal Light over the Atacama", "ZODIACAL"),
            ("An Analemma of the Sun", "ANALEMMA"),
            ("Copernicus Crater from Orbit", "CRATER"),
            ("Noctilucent Clouds over Warsaw", "NOCTILUCENT"),
            ("Airglow Ripples above Chile", "AIRGLOW"),
            ("Gegenschein in a Dark Sky", "GEGENSCHEIN"),
            ("The Milky Way above a Salt Flat", "MILKYWAY"),
            ("A Sunspot Up Close", "SUNSPOT"),
            ("The Pillars of Creation", "PILLAR"),
            ("Lunar Libration Cycle", "LIBRATION"),
        ]:
            with self.subTest(title=title):
                self.assertEqual(apod.derive_name(title, COMET_ASIDE), expected)

    def test_supernova_is_not_swallowed_by_nova(self):
        self.assertEqual(apod.derive_name("The Ghosts of Five Supernovas"), "SUPERNOVA")

    def test_the_verb_form_counts_too(self):
        self.assertEqual(apod.derive_name("A Daytime Eclipse: Moon Occults Venus"),
                         "OCCULTATION")


class FalseFriends(unittest.TestCase):
    """A constellation or a town is not a phenomenon."""

    def test_corona_australis_is_a_constellation(self):
        self.assertNotEqual(
            apod.derive_name("The Corona Australis Molecular Cloud"), "CORONA")

    def test_a_real_corona_still_reads_as_one(self):
        self.assertEqual(apod.derive_name("The Solar Corona in Totality"), "CORONA")

    def test_nova_scotia_is_a_place(self):
        self.assertNotEqual(apod.derive_name("Northern Lights over Nova Scotia"), "NOVA")


class TheExplanationIsOnlyAFallback(unittest.TestCase):
    def test_a_title_without_a_phenomenon_keeps_its_own_words(self):
        self.assertEqual(
            apod.derive_name("Daytime Moon Meets Evening Star", COMET_ASIDE), "MOON")
        self.assertEqual(apod.derive_name("Shadows at Rocky Point", ""), "SHADOWS.ROCKY")

    def test_the_explanation_is_read_only_when_the_title_has_no_subject(self):
        self.assertEqual(apod.derive_name("", COMET_ASIDE), "COMET")
        self.assertEqual(apod.derive_name("The of a", COMET_ASIDE), "COMET")

    def test_nothing_anywhere_still_produces_a_name(self):
        self.assertEqual(apod.derive_name("", ""), "APOD")


class TheApodLink(unittest.TestCase):
    def test_the_url_is_derived_exactly_from_the_iso_date(self):
        self.assertEqual(apod.apod_article_url("2026-09-24"),
                         "https://apod.nasa.gov/apod/ap260924.html")
        self.assertEqual(apod.apod_article_url("2026-06-01"),
                         "https://apod.nasa.gov/apod/ap260601.html")

    def test_a_date_that_is_not_a_day_has_no_article(self):
        for date in ("manual", "today", "", None, "2026-9-4"):
            with self.subTest(date=date):
                self.assertIsNone(apod.apod_article_url(date))


class TheCaptionTellsTheTruth(unittest.TestCase):
    def setUp(self):
        self.caption = apod.build_caption(sample_brief())

    def test_the_old_call_still_works_and_still_returns_the_feed_caption(self):
        self.assertIsInstance(self.caption, str)
        self.assertEqual(self.caption,
                         apod.build_caption(sample_brief(), channel="instagram",
                                            format="image"))

    def test_it_opens_on_the_source_title(self):
        self.assertTrue(self.caption.startswith("The Ghosts of Five Supernovas"),
                        self.caption)

    def test_the_discarded_claims_are_gone(self):
        for banned in ("rendered in code", "Save this sky", "send it to someone",
                       "#creativecodeart", "I shot", "I photographed"):
            for channel in apod.CHANNELS:
                for fmt in apod.FORMATS:
                    text = apod.build_caption(sample_brief(), channel=channel, format=fmt)
                    with self.subTest(banned=banned, channel=channel, format=fmt):
                        self.assertNotIn(banned, text)

    def test_every_surface_says_the_image_is_made_not_captured(self):
        for channel in apod.CHANNELS:
            for fmt in apod.FORMATS:
                text = apod.build_caption(sample_brief(), channel=channel, format=fmt)
                with self.subTest(channel=channel, format=fmt):
                    self.assertTrue("AI" in text, text)

    def test_it_links_the_exact_apod_article(self):
        self.assertIn("https://apod.nasa.gov/apod/ap260924.html", self.caption)

    def test_a_manual_run_links_nothing(self):
        text = apod.build_caption(sample_brief(date="manual", apod_url=None,
                                               apod_title="Validation subject"))
        self.assertNotIn("apod.nasa.gov", text)
        self.assertNotIn("None", text)

    def test_it_carries_the_photographer_when_apod_names_one(self):
        text = apod.build_caption(sample_brief(attribution="Jane Doe"))
        self.assertIn("Jane Doe", text)
        self.assertNotIn("Jane Doe", self.caption)  # not invented when absent

    def test_three_to_five_relevant_tags(self):
        for channel in apod.CHANNELS:
            for fmt in apod.FORMATS:
                text = apod.build_caption(sample_brief(), channel=channel, format=fmt)
                tags = text.strip().splitlines()[-1].split()
                with self.subTest(channel=channel, format=fmt):
                    self.assertTrue(all(t.startswith("#") for t in tags), tags)
                    self.assertEqual(len(tags), len(set(tags)))
                    self.assertGreaterEqual(len(tags), 3)
                    self.assertLessEqual(len(tags), 5)
                    self.assertIn("#supernova", tags)

    def test_it_stays_short(self):
        for channel in apod.CHANNELS:
            for fmt in apod.FORMATS:
                text = apod.build_caption(sample_brief(), channel=channel, format=fmt)
                with self.subTest(channel=channel, format=fmt):
                    self.assertLess(len(text), 700, text)

    def test_a_sparse_brief_does_not_crash(self):
        text = apod.build_caption({"date": "2026-09-24"})
        self.assertIn("2026-09-24", text)

    def test_an_unknown_surface_is_refused(self):
        with self.assertRaises(ValueError):
            apod.build_caption(sample_brief(), channel="threads")
        with self.assertRaises(ValueError):
            apod.build_caption(sample_brief(), format="carousel")


class EachSurfaceGetsItsOwnText(unittest.TestCase):
    def test_no_two_surfaces_share_a_caption(self):
        texts = [apod.build_caption(sample_brief(), channel=c, format=f)
                 for c in apod.CHANNELS for f in apod.FORMATS]
        self.assertEqual(len(texts), len(set(texts)))

    def test_the_reel_text_describes_a_reel(self):
        for channel in apod.CHANNELS:
            text = apod.build_caption(sample_brief(), channel=channel, format="reel")
            with self.subTest(channel=channel):
                self.assertIn("9:16", text)


class TheCaptionFiles(unittest.TestCase):
    def test_the_legacy_path_is_written_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy = os.path.join(tmp, "caption_2026-09-24.txt")
            apod.write_captions(sample_brief(), legacy)
            self.assertTrue(os.path.exists(legacy))
            self.assertEqual(Path(legacy).read_text(encoding="utf-8"),
                             apod.build_caption(sample_brief()))

    def test_the_three_siblings_are_named_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy = os.path.join(tmp, "caption_2026-09-24.txt")
            apod.write_captions(sample_brief(), legacy)
            self.assertEqual(
                sorted(os.listdir(tmp)),
                ["caption_2026-09-24.txt",
                 "caption_2026-09-24_facebook.txt",
                 "caption_2026-09-24_reel_facebook.txt",
                 "caption_2026-09-24_reel_instagram.txt"])

    def test_each_file_holds_its_own_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy = os.path.join(tmp, "caption_2026-09-24.txt")
            written = apod.write_captions(sample_brief(), legacy)
            for path, (channel, fmt) in written.items():
                with self.subTest(path=os.path.basename(path)):
                    self.assertEqual(Path(path).read_text(encoding="utf-8"),
                                     apod.build_caption(sample_brief(), channel=channel,
                                                        format=fmt))

    def test_the_suffix_lands_before_the_extension(self):
        self.assertEqual(apod.caption_variant_path("daily/caption_2026-09-24.txt", "_facebook"),
                         "daily/caption_2026-09-24_facebook.txt")
        self.assertEqual(apod.caption_variant_path("daily/caption_2026-09-24.txt", ""),
                         "daily/caption_2026-09-24.txt")


class TheBrief(unittest.TestCase):
    def test_the_existing_keys_keep_their_meaning(self):
        brief = apod.build_brief("2026-09-24", "The Ghosts of Five Supernovas",
                                 "SUPERNOVA", "200 hr", "prompt…",
                                 src_url="https://apod.nasa.gov/apod/image/2609/x.jpg",
                                 explanation="text", attribution="Jane Doe")
        self.assertEqual(brief["source"], "https://apod.nasa.gov/apod/image/2609/x.jpg")
        self.assertEqual(brief["label"], "namecode - SUPERNOVA | 200 hr")
        self.assertEqual(brief["date"], "2026-09-24")
        self.assertEqual(brief["apod_title"], "The Ghosts of Five Supernovas")
        self.assertEqual(brief["work_name"], "SUPERNOVA")
        self.assertIn("prompt", brief)

    def test_the_new_metadata_is_added(self):
        brief = apod.build_brief("2026-09-24", "T", "N", "v", "p",
                                 explanation="text", attribution="Jane Doe")
        self.assertEqual(brief["apod_url"], "https://apod.nasa.gov/apod/ap260924.html")
        self.assertEqual(brief["explanation"], "text")
        self.assertEqual(brief["attribution"], "Jane Doe")
        self.assertIsInstance(json.dumps(brief), str)

    def test_absent_metadata_is_left_out_rather_than_faked(self):
        brief = apod.build_brief("manual", "T", "N", "v", "p")
        self.assertNotIn("apod_url", brief)
        self.assertNotIn("attribution", brief)
        self.assertNotIn("explanation", brief)
        self.assertIsNone(brief["source"])


if __name__ == "__main__":
    unittest.main()
