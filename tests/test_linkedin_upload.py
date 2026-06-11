import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "linkedin_upload.py"
SPEC = importlib.util.spec_from_file_location("linkedin_upload", MODULE_PATH)
linkedin_upload = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(linkedin_upload)


class LinkedInUploadTests(unittest.TestCase):
    def test_validate_item_accepts_image_post(self):
        item = {
            "commentary": "과학을 고객의 언어로 번역합니다.",
            "image_url": "https://example.com/card.jpg",
            "scheduled_time": "2026-06-12T09:00:00+09:00",
        }
        self.assertEqual(linkedin_upload.validate_item(item), [])

    def test_create_post_uses_versioned_posts_payload(self):
        with patch.object(
            linkedin_upload,
            "_request_json",
            return_value=({}, {"x-restli-id": "urn:li:share:123"}),
        ) as request_json:
            post_urn = linkedin_upload.create_post(
                "token",
                "urn:li:organization:42",
                "본문",
                "urn:li:image:abc",
                "대체 텍스트",
            )

        self.assertEqual(post_urn, "urn:li:share:123")
        method, url, token, payload = request_json.call_args.args
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://api.linkedin.com/rest/posts")
        self.assertEqual(token, "token")
        self.assertEqual(payload["author"], "urn:li:organization:42")
        self.assertEqual(payload["content"]["media"]["id"], "urn:li:image:abc")
        self.assertEqual(payload["lifecycleState"], "PUBLISHED")

    def test_queue_round_trip_preserves_korean(self):
        with tempfile.TemporaryDirectory() as directory:
            queue_path = Path(directory) / "queue.json"
            original_path = linkedin_upload.QUEUE_FILE
            linkedin_upload.QUEUE_FILE = queue_path
            try:
                queue = {"items": [{"commentary": "기술은 정확하게, 메시지는 쉽게."}]}
                linkedin_upload.save_queue(queue)
                self.assertEqual(linkedin_upload.load_queue(), queue)
                self.assertIn("기술은 정확하게", queue_path.read_text(encoding="utf-8"))
            finally:
                linkedin_upload.QUEUE_FILE = original_path


if __name__ == "__main__":
    unittest.main()
