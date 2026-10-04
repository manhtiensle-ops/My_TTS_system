import os
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from engine import VieNeuEngine
from schemas import SpeechRequest, VoicesResponse, VoiceItem, HealthResponse

class ServerConfig:
    """Cấu hình tham số môi trường."""
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "15186"))

class TTSApplication:
    """Class bao đóng FastAPI App và quản lý vòng đời ứng dụng."""

    def __init__(self):
        self.engine = VieNeuEngine()
        self.app = FastAPI(
            title="VieNeu-TTS OpenAI Compatible API",
            description="High-performance Vietnamese Text-to-Speech API Server powered by GPU CUDA",
            version="3.8.3",
            lifespan=self.lifespan_handler
        )
        self._configure_middlewares()
        self._register_routes()

    def _configure_middlewares(self) -> None:
        """Cấu hình CORS mở cho tất cả Client truy cập."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @asynccontextmanager
    async def lifespan_handler(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """Quản lý nạp model khi khởi động và dọn dẹp khi tắt tiến trình."""
        print("[Startup] Bắt đầu nạp VieNeu-TTS vào GPU VRAM...")
        # Đẩy quá trình nạp model nặng ra một background thread để không chặn Event Loop
        await asyncio.to_thread(self.engine.load_model)
        print("[Startup] Mô hình đã sẵn sàng nhận request.")
        yield
        print("[Shutdown] Đang giải phóng VRAM GPU...")
        await asyncio.to_thread(self.engine.unload_model)
        print("[Shutdown] Hoàn tất tắt máy chủ.")

    def _register_routes(self) -> None:
        """Đăng ký các endpoints theo cấu trúc REST."""

        @self.app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
        async def health_check():
            is_cuda, device_name, vram_mb = self.engine.get_cuda_status()
            if not self.engine.is_loaded:
                return Response(
                    content='{"status": "loading", "model_loaded": false}',
                    media_type="application/json",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            return HealthResponse(
                status="ok",
                model_loaded=True,
                device=device_name,
                vram_used_mb=vram_mb
            )

        @self.app.get("/v1/voices", response_model=VoicesResponse, tags=["Audio"])
        async def list_voices():
            items = [VoiceItem(**item) for item in self.engine.VOICE_METADATA]
            return VoicesResponse(voices=items)

        @self.app.post("/v1/audio/speech", tags=["Audio"])
        async def generate_speech(request: SpeechRequest):
            canonical_voice = self.engine.resolve_voice(request.voice)
            if not canonical_voice:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Voice '{request.voice}' không tồn tại. Dùng GET /v1/voices để xem danh sách."
                )

            try:
                # Đẩy toàn bộ quá trình tính toán GPU ra Worker Thread của ThreadPoolExecutor
                audio_bytes = await asyncio.to_thread(
                    self.engine.synthesize,
                    text=request.input,
                    voice_name=canonical_voice,
                    speed=request.speed,
                    response_format=request.response_format
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Inference failed: {str(e)}"
                )

            media_type = "audio/wav" if request.response_format == "wav" else "audio/mpeg"
            return Response(
                content=audio_bytes,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="speech.{request.response_format}"'
                }
            )

# Khởi tạo instance server
server_app = TTSApplication()
app = server_app.app

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=False,
        workers=1 # Khuyên dùng 1 worker để giữ 1 instance CUDA Graph trên 1 GPU process
    )