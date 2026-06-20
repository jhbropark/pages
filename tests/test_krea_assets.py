import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "scaffold_krea_assets.py"
SPEC = importlib.util.spec_from_file_location("scaffold_krea_assets", MODULE_PATH)
scaffold_krea_assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scaffold_krea_assets)


class KreaAssetsTests(unittest.TestCase):
    def test_reel_concept_has_video_asset(self):
        concept = {"slug": "x", "pillar_id": "moa_craft", "has_reel": True}
        files = [a["file"] for a in scaffold_krea_assets.expected_assets(concept)]
        self.assertIn("reel.mp4", files)

    def test_non_reel_concept_has_no_video(self):
        concept = {"slug": "x", "pillar_id": "science_communication", "has_reel": False}
        kinds = {a["kind"] for a in scaffold_krea_assets.expected_assets(concept)}
        self.assertNotIn("video", kinds)

    def test_concept_has_six_instagram_cards_and_two_linkedin(self):
        concept = {"slug": "x", "has_reel": False}
        assets = scaffold_krea_assets.expected_assets(concept)
        instagram = [a for a in assets if a["channel"] == "instagram"]
        linkedin = [a for a in assets if a["channel"] == "linkedin"]
        self.assertEqual(len(instagram), scaffold_krea_assets.INSTAGRAM_CARD_COUNT)
        self.assertEqual(len(linkedin), 2)

    def test_linkedin_assets_use_landscape_size(self):
        concept = {"slug": "x", "has_reel": False}
        for asset in scaffold_krea_assets.expected_assets(concept):
            if asset["channel"] == "linkedin":
                self.assertEqual(asset["size"], list(scaffold_krea_assets.LINKEDIN_SIZE))

    def test_manifest_lists_all_pilot_concepts(self):
        manifest = scaffold_krea_assets.build_manifest(
            "test-batch", scaffold_krea_assets.PILOT_CONCEPTS
        )
        self.assertEqual(manifest["batch"], "test-batch")
        slugs = {c["slug"] for c in manifest["concepts"]}
        self.assertEqual(
            slugs,
            {c["slug"] for c in scaffold_krea_assets.PILOT_CONCEPTS},
        )

    def test_dm_keywords_are_unique(self):
        keywords = [c["dm_keyword"] for c in scaffold_krea_assets.PILOT_CONCEPTS]
        self.assertEqual(len(keywords), len(set(keywords)))


if __name__ == "__main__":
    unittest.main()
