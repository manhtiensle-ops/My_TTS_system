import asyncio
import os
import shutil
import uuid
from dataclasses import dataclass
from typing import Optional

from src.config import settings
from src.engines.base import BaseTTSEngine
from src.lifecycle.supervisor import get_supervisor
from src.processors.audio_concat import AudioConcatenator
from src.processors.text_splitter import NovelTextSplitter


@dataclass
class NovelResult:
    """Kết quả hoàn thành của pipeline xử lý truyện."""
    audio_bytes: bytes
    total_chunks: int
    filename: str
    media_type: str


class NovelPipelineService:
    """Service điều phối toàn bộ chu trình xử lý truyện tiểu thuyết dài."""

    def __init__(
        self,
        engine: Optional[BaseTTSEngine] = None,
        splitter: Optional[NovelTextSplitter] = None,
        concatenator: Optional[AudioConcatenator] = None,
        tmp_base: Optional[str] = None,
    ):
        self.engine = engine
        self.supervisor = get_supervisor()
        self.splitter = splitter or NovelTextSplitter()
        self.concatenator = concatenator or AudioConcatenator()
        self.tmp_base = tmp_base or settings.TMP_DIR

    async def _synthesize_chunk(self, chunk: str, voice_name: str, speed: float) -> bytes:
        if self.engine is not None and getattr(self.engine, "is_loaded", False):
            return await asyncio.to_thread(
                self.engine.synthesize,
                text=chunk,
                voice_name=voice_name,
                speed=speed,
                response_format="wav",
            )
        else:
            return await self.supervisor.synthesize(
                text=chunk,
                voice=voice_name,
                speed=speed,
                response_format="wav",
            )

    async def process_novel(
        self,
        text: str,
        voice_name: str,
        speed: float = 1.2,
        response_format: str = "wav",
        chapter_name: str = "",
        target_words: int = 100,
    ) -> NovelResult:
        """Thực thi pipeline hoàn chỉnh cho 1 chapter truyện."""
        chunks = self.splitter.split(text, target_words=target_words)
        if not chunks:
            raise ValueError("Nội dung chapter rỗng hoặc không chứa văn bản hợp lệ.")

        total_chunks = len(chunks)
        job_id = uuid.uuid4().hex[:12]
        work_dir = os.path.join(self.tmp_base, f"tts_novel_{job_id}")
        os.makedirs(work_dir, exist_ok=True)
        wav_parts = []

        try:
            for i, chunk in enumerate(chunks):
                part_path = os.path.join(work_dir, f"part_{i:04d}.wav")
                try:
                    audio_bytes = await self._synthesize_chunk(chunk, voice_name, speed)
                except Exception as e:
                    raise RuntimeError(f"Lỗi inference tại đoạn {i + 1}/{total_chunks}: {str(e)}") from e

                with open(part_path, "wb") as f:
                    f.write(audio_bytes)
                wav_parts.append(part_path)

            ext = response_format.lower()
            output_path = os.path.join(work_dir, f"final.{ext}")
            await asyncio.to_thread(self.concatenator.concat, wav_parts, output_path)

            with open(output_path, "rb") as f:
                final_bytes = f.read()

            raw_name = chapter_name.strip() or f"novel_{job_id}"
            safe_name = raw_name.replace(" ", "_")
            media_type = "audio/wav" if ext == "wav" else "audio/mpeg"

            return NovelResult(
                audio_bytes=final_bytes,
                total_chunks=total_chunks,
                filename=f"{safe_name}.{ext}",
                media_type=media_type,
            )

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
