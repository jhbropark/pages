import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ContentStrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ROOT / "content" / "strategy.json", encoding="utf-8") as handle:
            cls.strategy = json.load(handle)
        with open(ROOT / "content" / "topics.json", encoding="utf-8") as handle:
            cls.topics = json.load(handle)

    def test_pillar_weights_total_100(self):
        total = sum(pillar["weight"] for pillar in self.strategy["pillars"])
        self.assertEqual(total, 100)

    def test_twenty_post_cycle_matches_weights(self):
        pillars = {pillar["id"]: pillar for pillar in self.strategy["pillars"]}
        cycle = self.strategy["pillar_cycle_20_posts"]
        self.assertEqual(len(cycle), 20)
        counts = Counter(cycle)
        for pillar_id, pillar in pillars.items():
            expected = pillar["weight"] * len(cycle) // 100
            self.assertEqual(counts[pillar_id], expected)

    def test_every_pillar_has_topics(self):
        pillar_ids = {pillar["id"] for pillar in self.strategy["pillars"]}
        topic_pillars = {topic["pillar_id"] for topic in self.topics["topic_bank"]}
        self.assertEqual(topic_pillars, pillar_ids)

    def test_channel_and_schedule_rules(self):
        channels = self.strategy["channels"]
        self.assertEqual(channels["instagram"]["caption_max_chars"], 220)
        self.assertEqual(channels["instagram"]["carousel_cards"], {"min": 4, "max": 6})
        self.assertEqual(channels["linkedin"]["hashtags"], {"min": 3, "max": 4})
        every_day = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        self.assertEqual(self.strategy["operations"]["publish_days"], every_day)
        self.assertEqual(self.strategy["operations"]["draft_days"], every_day)
        self.assertEqual(self.strategy["operations"]["daily_frequency"], 2)
        self.assertEqual(
            channels["instagram"]["publish_times_kst"],
            ["12:30", "19:00"],
        )
        self.assertEqual(
            channels["linkedin"]["publish_times_kst"],
            ["09:00", "15:00"],
        )

    def test_visual_color_ratios_total_100(self):
        colors = self.strategy["visual_system"]["colors"]
        self.assertEqual(sum(color["ratio"] for color in colors.values()), 100)


if __name__ == "__main__":
    unittest.main()
