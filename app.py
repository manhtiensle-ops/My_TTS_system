import os
import uuid
import shutil
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from engine import VieNeuEngine
from schemas import SpeechRequest, NovelRequest, VoicesResponse, VoiceItem, HealthResponse
from text_splitter import split_chapter
from audio_concat import concat_wav_files


class ServerConfig:
    """Cấu hình tham số môi trường."""
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "7865"))

# Thư mục chứa file tạm khi xử lý truyện dài
TMP_BASE = os.getenv("TTS_TMP_DIR", "/tmp")


class TTSApplication:
    """Class bao đóng FastAPI App và quản lý vòng đời ứng dụng."""

    def __init__(self):
        self.engine = VieNeuEngine()
        self.app = FastAPI(
            title="VieNeu-TTS API Server",
            description="Vietnamese TTS — Video Shorts (Trúc Ly) + Novel Reader (Ngọc Huyền)",
            version="1.0.0",
            lifespan=self.lifespan_handler,
        )
        self._configure_middlewares()
        self._register_routes()

    def _configure_middlewares(self) -> None:
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @asynccontextmanager
    async def lifespan_handler(self, app: FastAPI) -> AsyncGenerator[None, None]:
        print("[Startup] Bắt đầu nạp VieNeu-TTS vào GPU VRAM...")
        await asyncio.to_thread(self.engine.load_model)
        print("[Startup] Mô hình đã sẵn sàng nhận request.")
        yield
        print("[Shutdown] Đang giải phóng VRAM GPU...")
        await asyncio.to_thread(self.engine.unload_model)
        print("[Shutdown] Hoàn tất tắt máy chủ.")

    def _register_routes(self) -> None:

        # ── GET /health ─────────────────────────────────────────
        @self.app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
        async def health_check():
            is_cuda, device_name, vram_mb = self.engine.get_cuda_status()
            if not self.engine.is_loaded:
                return Response(
                    content='{"status": "loading", "model_loaded": false}',
                    media_type="application/json",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return HealthResponse(
                status="ok",
                model_loaded=True,
                device=device_name,
                vram_used_mb=vram_mb,
            )

        # ── GET /v1/voices ──────────────────────────────────────
        @self.app.get("/v1/voices", response_model=VoicesResponse, tags=["Audio"])
        async def list_voices():
            items = [VoiceItem(**item) for item in self.engine.VOICE_METADATA]
            return VoicesResponse(voices=items)

        # ── POST /v1/audio/speech — TTS ngắn (Video Shorts) ────
        @self.app.post("/v1/audio/speech", tags=["Audio"])
        async def generate_speech(request: SpeechRequest):
            canonical_voice = self.engine.resolve_voice(request.voice)
            if not canonical_voice:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Voice '{request.voice}' không tồn tại. Dùng GET /v1/voices để xem danh sách.",
                )

            try:
                audio_bytes = await asyncio.to_thread(
                    self.engine.synthesize,
                    text=request.input,
                    voice_name=canonical_voice,
                    speed=request.speed,
                    response_format=request.response_format,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Inference failed: {str(e)}",
                )

            media_type = "audio/wav" if request.response_format == "wav" else "audio/mpeg"
            return Response(
                content=audio_bytes,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="speech.{request.response_format}"'
                },
            )

        # ── POST /v1/audio/novel — TTS truyện dài ──────────────
        @self.app.post("/v1/audio/novel", tags=["Novel"])
        async def generate_novel_audio(request: NovelRequest):
            # 1. Validate voice
            canonical_voice = self.engine.resolve_voice(request.voice)
            if not canonical_voice:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Voice '{request.voice}' không tồn tại. Dùng GET /v1/voices để xem danh sách.",
                )

            # 2. Chia nhỏ text
            chunks = split_chapter(request.input, target_words=request.target_words)
            if not chunks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Input text rỗng hoặc không có nội dung hợp lệ.",
                )

            total_chunks = len(chunks)
            job_id = uuid.uuid4().hex[:12]
            work_dir = os.path.join(TMP_BASE, f"tts_novel_{job_id}")
            os.makedirs(work_dir, exist_ok=True)

            wav_parts: list[str] = []

            try:
                # 3. TTS từng đoạn nhỏ → file WAV tạm
                for i, chunk in enumerate(chunks):
                    part_path = os.path.join(work_dir, f"part_{i:04d}.wav")
                    try:
                        audio_bytes = await asyncio.to_thread(
                            self.engine.synthesize,
                            text=chunk,
                            voice_name=canonical_voice,
                            speed=request.speed,
                            response_format="wav",
                        )
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Inference thất bại tại đoạn {i + 1}/{total_chunks}: {str(e)}",
                        )

                    with open(part_path, "wb") as f:
                        f.write(audio_bytes)
                    wav_parts.append(part_path)

                # 4. Nối tất cả WAV thành 1 file hoàn chỉnh
                ext = request.response_format
                output_path = os.path.join(work_dir, f"final.{ext}")
                await asyncio.to_thread(concat_wav_files, wav_parts, output_path)

                # 5. Đọc binary trả về client
                with open(output_path, "rb") as f:
                    final_bytes = f.read()

                media_type = "audio/wav" if ext == "wav" else "audio/mpeg"
                filename = request.chapter_name or f"novel_{job_id}"
                filename = filename.replace(" ", "_")

                return Response(
                    content=final_bytes,
                    media_type=media_type,
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}.{ext}"',
                        "X-TTS-Chunks": str(total_chunks),
                    },
                )

            finally:
                # 6. Dọn sạch thư mục tạm
                shutil.rmtree(work_dir, ignore_errors=True)


# Khởi tạo instance server
server_app = TTSApplication()
app = server_app.app

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=False,
        workers=1,  # 1 worker giữ 1 instance CUDA Graph trên 1 GPU process
    )
