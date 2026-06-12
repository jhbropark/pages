import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "instagram_upload.py"
SPEC = importlib.util.spec_from_file_location("instagram_upload", MODULE_PATH)
instagram_upload = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(instagram_upload)


class InstagramUploadTests(unittest.TestCase):
    def test_instagram_login_token_uses_instagram_graph(self):
        token = "IGAA" + "x" * 60
        self.assertEqual(
            instagram_upload._resolve_api_base(token),
            "https://graph.instagram.com/v25.0",
        )

    def test_numeric_account_id_is_rejected_as_access_token(self):
        with self.assertRaisesRegex(ValueError, "계정 ID"):
            instagram_upload._resolve_api_base("17841234567890123")

    def test_short_token_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "너무 짧습니다"):
            instagram_upload._resolve_api_base("not-a-token")

    def test_facebook_token_diagnoses_configured_instagram_account(self):
        instagram_upload.GRAPH_API_BASE = "https://graph.facebook.com/v25.0"
        with patch.object(
            instagram_upload,
            "_api_get",
            side_effect=[
                {
                    "id": "17841234567890123",
                    "username": "bbbb.beauty_official",
                },
                {"data": []},
                {"data": []},
            ],
        ) as api_get:
            resolved_id = instagram_upload.diagnose_access(
                "EAAm-token",
                "17841234567890123",
            )

        self.assertEqual(resolved_id, "17841234567890123")
        self.assertEqual(api_get.call_args_list[0].args[0], "17841234567890123")

    def test_facebook_token_requires_configured_instagram_account(self):
        instagram_upload.GRAPH_API_BASE = "https://graph.facebook.com/v25.0"
        with self.assertRaisesRegex(RuntimeError, "INSTAGRAM_USER_ID"):
            instagram_upload.diagnose_access("EAAm-token")

    def test_carousel_accepts_two_to_ten_images(self):
        item = {
            "image_urls": [
                "https://example.com/slide-1.jpg",
                "https://example.com/slide-2.jpg",
            ],
            "caption": "Test",
            "hashtags": [],
            "scheduled_time": "2026-06-12T00:00:00+00:00",
        }
        self.assertEqual(instagram_upload.validate_item(item), [])

    def test_carousel_rejects_single_image(self):
        item = {
            "image_urls": ["https://example.com/slide-1.jpg"],
            "caption": "Test",
            "hashtags": [],
            "scheduled_time": "2026-06-12T00:00:00+00:00",
        }
        self.assertIn(
            "image_urls는 2~10장의 이미지여야 합니다.",
            instagram_upload.validate_item(item),
        )

    def test_local_mp4_rejects_edit_lists(self):
        media_path = (
            Path(__file__).parents[1]
            / "images"
            / "test-meta-edit-list.mp4"
        )
        try:
            media_path.write_bytes(b"\x00\x00\x00\x18ftypisommoovedtselstmdat")
            errors = instagram_upload.inspect_local_mp4(
                "https://jhbropark.github.io/pages/images/test-meta-edit-list.mp4"
            )
            self.assertIn(
                "Meta가 허용하지 않는 MP4 편집 목록(edts/elst)이 포함되어 있습니다.",
                errors,
            )
        finally:
            media_path.unlink(missing_ok=True)

    def test_container_error_includes_meta_status_detail(self):
        with patch.object(
            instagram_upload,
            "_api_get",
            return_value={
                "status_code": "ERROR",
                "status": "Media download has failed.",
            },
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Media download has failed",
            ):
                instagram_upload.wait_for_container_ready(
                    "container-123",
                    "token",
                    timeout=1,
                    poll_interval=0,
                )

    def test_resumable_container_uploads_returned_uri(self):
        with (
            patch.object(
                instagram_upload,
                "_api_post",
                return_value={
                    "id": "container-123",
                    "uri": "https://rupload.facebook.com/upload/container-123",
                },
            ) as api_post,
            patch.object(
                instagram_upload,
                "_rupload_from_url",
                return_value={"success": True},
            ) as rupload,
        ):
            result = instagram_upload.create_resumable_video_container(
                "user-123",
                "token",
                "REELS",
                "https://example.com/reel.mp4",
                "Caption",
                share_to_feed=True,
            )

        self.assertEqual(result, "container-123")
        self.assertEqual(
            api_post.call_args.args[1]["upload_type"],
            "resumable",
        )
        rupload.assert_called_once_with(
            "https://rupload.facebook.com/upload/container-123",
            "token",
            "https://example.com/reel.mp4",
        )


if __name__ == "__main__":
    unittest.main()
