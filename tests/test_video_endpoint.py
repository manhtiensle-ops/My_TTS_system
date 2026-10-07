import sys
from unittest.mock import AsyncMock, MagicMock

# Mock heavy GPU dependencies for unit tests if not installed
if "torch" not in sys.modules:
    sys.modules["torch"] = MagicMock()
if "vieneu" not in sys.modules:
    sys.modules["vieneu"] = MagicMock()

import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.dependencies import get_novel_video_service
from src.api.routes.video_novel import router
from src.services.novel_video_service import NovelVideoResult, NovelVideoService
from fastapi import FastAPI


class TestVideoEndpoint(unittest.TestCase):

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)

        self.mock_video_service = MagicMock(spec=NovelVideoService)
        self.mock_video_service.process_novel_video = AsyncMock(
            return_value=NovelVideoResult(
                video_bytes=b"fake mp4 video bytes",
                filename="Chuong_1.mp4",
                media_type="video/mp4",
            )
        )

        self.app.dependency_overrides[get_novel_video_service] = lambda: self.mock_video_service
        self.client = TestClient(self.app)

    def test_render_novel_video_success(self):
        files = {
            "cover_image": ("cover.jpg", b"fake image bytes", "image/jpeg"),
        }
        data = {
            "text": "Đây là nội dung chương 1 tiểu thuyết phàm nhân tu tiên.",
            "chapter_name": "Chương 1",
            "voice": "Ngọc Huyền",
            "speed": "1.2",
            "resolution": "1920x1080",
        }

        response = self.client.post("/v1/video/novel", data=data, files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")
        self.assertIn("filename*=UTF-8''Chuong_1.mp4", response.headers["content-disposition"])
        self.assertEqual(response.content, b"fake mp4 video bytes")

    def test_render_novel_video_empty_text(self):
        files = {
            "cover_image": ("cover.jpg", b"fake image bytes", "image/jpeg"),
        }
        data = {
            "text": "   ",
            "chapter_name": "Chương 1",
        }

        response = self.client.post("/v1/video/novel", data=data, files=files)
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
