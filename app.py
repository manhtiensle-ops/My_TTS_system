import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.router import api_router
from src.config import settings
from src.lifecycle.supervisor import get_supervisor


class TTSApplication:
    """Lớp bao đóng ứng dụng FastAPI với quản lý vòng đời GPU On-Demand (Zero-VRAM Baseline)."""

    def __init__(self):
        self.supervisor = get_supervisor()
        self.app = FastAPI(
            title="VieNeu-TTS API Server",
            description="Vietnamese TTS Server — On-Demand VRAM Lifecycle Controller (Trúc Ly 1.1 & Ngọc Huyền 1.2)",
            version="1.2.0",
            lifespan=self.lifespan_handler,
        )
        self._configure_middlewares()
        self._configure_routes()

    def _configure_middlewares(self) -> None:
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _configure_routes(self) -> None:
        self.app.include_router(api_router)

    @asynccontextmanager
    async def lifespan_handler(self, app: FastAPI) -> AsyncGenerator[None, None]:
        print("[Startup] Lightweight Control Daemon ready (Zero-VRAM baseline: SLEEP).")
        yield
        print("[Shutdown] Thu hồi tài nguyên và giải phóng GPU Worker process...")
        await self.supervisor.unload_model(force=True)
        print("[Shutdown] Hoàn tất tắt máy chủ.")


# Khởi tạo singleton app
server_app = TTSApplication()
app = server_app.app


def main():
    """Hàm khởi chạy máy chủ qua Uvicorn."""
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        workers=1,  # 1 worker duy trì 1 instance CUDA Graph trên GPU
    )


if __name__ == "__main__":
    main()
