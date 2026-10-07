import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from vieneu_sdk.youtube.config import YouTubeConfig
from vieneu_sdk.youtube.quota import QuotaTracker
from vieneu_sdk.youtube.metadata import NovelMetadataBuilder, VideoMetadata
from vieneu_sdk.youtube.uploader import YouTubeUploader, UploadResult


class TestYouTubeSDK(unittest.TestCase):

    def test_youtube_metadata_builder(self):
        builder = NovelMetadataBuilder(novel_title="Phàm Nhân Tu Tiên", author="Vong Ngữ")
        meta = builder.build_for_chapter(
            chapter_name="Khởi Đầu",
            chapter_number=1.0,
            privacy="unlisted",
            playlist_id="PL12345",
        )
        self.assertIn("Phàm Nhân Tu Tiên", meta.title)
        self.assertIn("Tập 1", meta.title)
        self.assertEqual(meta.privacy_status, "unlisted")
        self.assertEqual(meta.playlist_id, "PL12345")
        self.assertIn("#phàmnhântutiên", meta.description)

    def test_quota_tracker(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_file = Path(tmp_dir) / "quota.json"
            tracker = QuotaTracker(cache_file=cache_file)

            self.assertTrue(tracker.can_upload())
            tracker.consume(5000)
            self.assertTrue(tracker.can_upload())

            # Consuming up to daily limit
            tracker.consume(4000)  # total 9000
            self.assertFalse(tracker.can_upload(has_thumbnail=True, has_playlist=True))  # 9000 + 1700 > 10000

    def test_youtube_config_from_env(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text(
                "YOUTUBE_CLIENT_ID=test_id_123\nYOUTUBE_CLIENT_SECRET=test_secret_abc\n",
                encoding="utf-8",
            )
            config = YouTubeConfig.from_env(env_path=env_file)
            self.assertEqual(config.client_id, "test_id_123")
            self.assertEqual(config.client_secret, "test_secret_abc")

    @patch("vieneu_sdk.youtube.auth.YouTubeAuthManager")
    def test_youtube_uploader_quota_exceeded(self, mock_auth):
        with tempfile.TemporaryDirectory() as tmp_dir:
            quota_file = Path(tmp_dir) / "quota.json"
            tracker = QuotaTracker(cache_file=quota_file)
            tracker.consume(9900)  # Almost max

            uploader = YouTubeUploader(auth_manager=mock_auth, quota_tracker=tracker)

            video_file = Path(tmp_dir) / "test.mp4"
            video_file.write_bytes(b"fake video")

            meta = VideoMetadata(title="Test", description="Desc")
            res = uploader.upload_video(video_path=video_file, metadata=meta)

            self.assertEqual(res.status, "quota_exceeded")


if __name__ == "__main__":
    unittest.main()
