import asyncio
import os
import shutil
import uuid
from dataclasses import dataclass

from src.config import settings
from src.processors.video_renderer import StillImageVideoRenderer
from src.services.novel_service import NovelPipelineService


@dataclass
class NovelVideoResult:
    """Kết quả hoàn thành của pipeline render video truyện."""
    video_bytes: bytes
    filename: str
    media_type: str = "video/mp4"


class NovelVideoService:
    """Service điều phối toàn bộ chu trình xử lý TTS + Render Video MP4."""

    def __init__(
        self,
        novel_service: NovelPipelineService,
        renderer: StillImageVideoRenderer | None = None,
        tmp_base: str | None = None,
    ):
        self.novel_service = novel_service
        self.renderer = renderer or StillImageVideoRenderer()
        self.tmp_base = tmp_base or settings.TMP_DIR

    async def process_novel_video(
        self,
        text: str,
        cover_bytes: bytes,
        cover_filename: str,
        voice_name: str = "Ngọc Huyền",
        speed: float = 1.2,
        chapter_name: str = "",
        resolution: str = "1920x1080",
        target_words: int = 100,
    ) -> NovelVideoResult:
        """Thực thi pipeline hoàn chỉnh cho 1 chapter truyện -> MP4."""
        job_id = uuid.uuid4().hex[:12]
        work_dir = os.path.join(self.tmp_base, f"tts_video_{job_id}")
        os.makedirs(work_dir, exist_ok=True)

        try:
            # 1. Sinh audio mp3 qua NovelPipelineService
            audio_result = await self.novel_service.process_novel(
                text=text,
                voice_name=voice_name,
                speed=speed,
                response_format="mp3",
                chapter_name=chapter_name,
                target_words=target_words,
            )

            audio_path = os.path.join(work_dir, "audio.mp3")
            with open(audio_path, "wb") as f:
                f.write(audio_result.audio_bytes)

            # 2. Ghi file cover image tạm
            ext = os.path.splitext(cover_filename)[1] or ".jpg"
            cover_path = os.path.join(work_dir, f"cover{ext}")
            with open(cover_path, "wb") as f:
                f.write(cover_bytes)

            # 3. Render video MP4
            output_mp4 = os.path.join(work_dir, "output.mp4")
            await asyncio.to_thread(
                self.renderer.render_video,
                image_path=cover_path,
                audio_path=audio_path,
                output_path=output_mp4,
                resolution=resolution,
                fps=1,
            )

            # 4. Đọc nhị phân MP4
            with open(output_mp4, "rb") as f:
                video_bytes = f.read()

            raw_name = chapter_name.strip() or f"novel_{job_id}"
            safe_name = raw_name.replace(" ", "_")

            return NovelVideoResult(
                video_bytes=video_bytes,
                filename=f"{safe_name}.mp4",
                media_type="video/mp4",
            )

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
