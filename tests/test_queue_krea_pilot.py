import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "queue_krea_pilot.py"
SPEC = importlib.util.spec_from_file_location("queue_krea_pilot", MODULE_PATH)
queue_krea_pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(queue_krea_pilot)


NOW = "2026-06-20T00:00:00+00:00"


class QueueKreaPilotTests(unittest.TestCase):
    def setUp(self):
        self.ig_content = {
            "items": [
                {
                    "id": "krea-pilot-x",
                    "format": "carousel",
                    "topic": "t",
                    "pillar_id": "moa_craft",
                    "dm_keyword": "MOA",
                    "image_urls": ["a.jpg", "b.jpg"],
                    "caption": "c",
                    "hashtags": ["#a", "#bbbbbeauty"],
                    "alt_text": "alt",
                }
            ]
        }
        self.li_content = {
            "items": [
                {
                    "korean_id": "li_x",
                    "english_id": "li_x_en",
                    "pair_id": "li_x",
                    "topic": "t",
                    "pillar_id": "moa_craft",
                    "dm_keyword": "MOA",
                    "commentary_ko": "ko",
                    "commentary_en": "en",
                    "hashtags_ko": ["#a"],
                    "hashtags_en": ["#b"],
                    "image_url_ko": "ko.jpg",
                    "image_url_en": "en.jpg",
                    "alt_text": "alt",
                }
            ]
        }

    def test_instagram_items_are_draft_with_carousel(self):
        items = queue_krea_pilot.build_instagram_items(self.ig_content, NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "draft")
        self.assertEqual(items[0]["image_urls"], ["a.jpg", "b.jpg"])
        self.assertIsNone(items[0]["scheduled_time"])

    def test_linkedin_builds_ko_then_en_pair(self):
        items = queue_krea_pilot.build_linkedin_items(self.li_content, NOW)
        self.assertEqual([i["language"] for i in items], ["ko", "en"])
        self.assertEqual([i["pair_order"] for i in items], [1, 2])
        self.assertTrue(all(i["status"] == "draft" for i in items))
        self.assertEqual(items[0]["commentary"], "ko")
        self.assertEqual(items[1]["commentary"], "en")

    def test_merge_is_idempotent(self):
        queue = {"items": []}
        new = queue_krea_pilot.build_instagram_items(self.ig_content, NOW)
        first = queue_krea_pilot.merge_into_queue(queue, new)
        second = queue_krea_pilot.merge_into_queue(queue, new)
        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(len(queue["items"]), 1)


if __name__ == "__main__":
    unittest.main()
