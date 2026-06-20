import importlib.util
import unittest
from datetime import datetime
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "generate_content.py"
SPEC = importlib.util.spec_from_file_location("generate_content", MODULE_PATH)
generate_content = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_content)


class ContentConversionTests(unittest.TestCase):
    def setUp(self):
        self.content = {
            "caption": "복잡한 기술을 고객이 이해할 수 있는 장면으로 번역합니다.",
            "hashtags": [
                "#과학커뮤니케이션",
                "#바이오마케팅",
                "#메디컬콘텐츠",
                "#3D애니메이션",
                "#bbbbbeauty",
            ],
            "image_headline": "기술을 경험으로",
            "comment_question": "A 정확성 / B 몰입감, 무엇이 더 필요한가요?",
            "dm_keyword": "MOA",
            "dm_offer": "기술 시각화 진단 질문을 보내드립니다.",
            "english_image_headline": "TURN TECHNOLOGY INTO EXPERIENCE",
            "linkedin_ko": ("기술을 고객의 언어로 번역합니다. " * 70) + "MOA",
            "linkedin_en": (
                ("We translate complex science into a clear customer experience. " * 25)
                + "MOA"
            ),
            "linkedin_ko_hashtags": ["#과학커뮤니케이션", "#바이오마케팅", "#브랜드전략"],
            "linkedin_en_hashtags": ["#ScienceCommunication", "#BiotechMarketing", "#BrandStrategy"],
        }

    def test_caption_contains_three_conversion_paths(self):
        caption = generate_content.build_conversion_caption(self.content)
        self.assertIn("댓글:", caption)
        self.assertIn('DM “MOA”:', caption)
        self.assertIn("프로필 링크", caption)
        self.assertIn("저장·공유", caption)

    def test_valid_content_passes(self):
        self.assertEqual(
            generate_content.validate_generated_content(self.content),
            [],
        )

    def test_missing_dm_keyword_fails(self):
        self.content["dm_keyword"] = ""
        errors = generate_content.validate_generated_content(self.content)
        self.assertTrue(any("DM 키워드" in error for error in errors))

    def test_hashtag_without_hash_prefix_fails(self):
        self.content["hashtags"][0] = "과학커뮤니케이션"
        errors = generate_content.validate_generated_content(self.content)
        self.assertTrue(any("#으로 시작" in error for error in errors))

    def test_linkedin_hashtag_without_hash_prefix_fails(self):
        self.content["linkedin_en_hashtags"][0] = "ScienceCommunication"
        errors = generate_content.validate_generated_content(self.content)
        self.assertTrue(
            any("linkedin_en_hashtags" in error and "#으로 시작" in error for error in errors)
        )

    def test_two_daily_slots_select_different_topics(self):
        config = {
            "daily_slots": [{"id": "morning"}, {"id": "afternoon"}],
            "topics": ["A", "B", "C", "D"],
        }
        now = datetime(2026, 6, 13, tzinfo=generate_content.KST)
        selected = [
            generate_content.pick_topic(config, now, slot_index)
            for slot_index in range(2)
        ]
        self.assertEqual(len(set(selected)), 2)


if __name__ == "__main__":
    unittest.main()
