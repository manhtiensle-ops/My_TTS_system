"""
client.py — HTTP Client layer giao tiếp với VieNeu GPU Server.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class VieneuClient:
    """Client kết nối API VieNeu GPU Server."""

    def __init__(self, base_url: str = "http://100.90.61.115:7865", timeout: int = 900):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

        retries = Retry(total=3, backoff_factor=2, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def check_health(self) -> Dict[str, Any]:
        """Kiểm tra phản hồi sức khỏe GPU Server."""
        url = f"{self.base_url}/health"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def render_chapter_video(
        self,
        chapter_text: str,
        cover_image_path: Path,
        output_file_path: Path,
        chapter_name: str = "",
        voice: str = "Ngọc Huyền",
        speed: float = 1.2,
        resolution: str = "1920x1080",
        target_words: int = 100,
    ) -> Path:
        """Gửi request render video chapter truyện + ảnh bìa thành MP4.

        Args:
            chapter_text: Nội dung văn bản chapter.
            cover_image_path: Path file ảnh bìa (JPG/PNG).
            output_file_path: Path lưu file video MP4 kết quả.
            chapter_name: Tên chapter (tùy chọn).
            voice: Giọng đọc (mặc định 'Ngọc Huyền').
            speed: Tốc độ đọc (mặc định 1.2).
            resolution: Độ phân giải video.
            target_words: Số từ mỗi đoạn.

        Returns:
            Path file MP4 thành phẩm.
        """
        if not cover_image_path.exists():
            raise FileNotFoundError(f"File ảnh bìa không tồn tại: {cover_image_path}")

        url = f"{self.base_url}/v1/video/novel"

        data = {
            "text": chapter_text,
            "chapter_name": chapter_name,
            "voice": voice,
            "speed": str(speed),
            "resolution": resolution,
            "target_words": str(target_words),
        }

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(cover_image_path, "rb") as img_file:
            files = {
                "cover_image": (cover_image_path.name, img_file, "image/jpeg"),
            }

            response = self.session.post(
                url,
                data=data,
                files=files,
                timeout=self.timeout,
                stream=True,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Lỗi Server (HTTP {response.status_code}): {response.text}"
                )

            with open(output_file_path, "wb") as out_f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        out_f.write(chunk)

        return output_file_path
