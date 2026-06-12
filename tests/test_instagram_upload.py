import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "instagram_upload.py"
SPEC = importlib.util.spec_from_file_location("instagram_upload", MODULE_PATH)
instagram_upload = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(instagram_upload)


class InstagramUploadTests(unittest.TestCase):
    def test_instagram_login_token_uses_instagram_graph(self):
        token = "IGAA" + "x" * 60
        self.assertEqual(
            instagram_upload._resolve_api_base(token),
            "https://graph.instagram.com/v23.0",
        )

    def test_numeric_account_id_is_rejected_as_access_token(self):
        with self.assertRaisesRegex(ValueError, "계정 ID"):
            instagram_upload._resolve_api_base("17841234567890123")

    def test_short_token_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "너무 짧습니다"):
            instagram_upload._resolve_api_base("not-a-token")


if __name__ == "__main__":
    unittest.main()
