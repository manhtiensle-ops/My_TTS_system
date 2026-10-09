from typing import List, Optional
from pydantic import BaseModel, Field


class LoadModelRequest(BaseModel):
    model_name: str = Field(default="v3turbo", description="Phiên bản model VieNeu-TTS")
    voice_preload: List[str] = Field(
        default_factory=lambda: ["ngoc_huyen", "truc_ly"],
        description="Danh sách các giọng đọc cần nạp ấm",
    )
    idle_timeout_seconds: int = Field(
        default=600,
        ge=60,
        le=3600,
        description="Thời gian tự động ngắt GPU nếu không có request (giây)",
    )


class UnloadModelRequest(BaseModel):
    force: bool = Field(default=False, description="Cưỡng chế ngắt tiến trình ngầm tức thì")


class LifecycleStatusResponse(BaseModel):
    state: str = Field(..., description="Trạng thái FSM hiện tại (SLEEP, STARTING, READY, PROCESSING, STOPPING, ERROR)")
    vram_allocated_mb: float = Field(..., description="Dung lượng VRAM đang sử dụng (MB)")
    worker_pid: Optional[int] = Field(None, description="PID của tiến trình Worker ngầm")
    idle_seconds_remaining: float = Field(0.0, description="Số giây còn lại trước khi tự động xả VRAM")
    model_name: str = Field("v3turbo", description="Tên model VieNeu")
    loaded_voices: List[str] = Field(default_factory=list, description="Danh sách voice đang nạp")


class HeartbeatRequest(BaseModel):
    idle_timeout_seconds: Optional[int] = Field(None, ge=60, le=3600, description="Gia hạn thêm số giây đếm ngược")


class HeartbeatResponse(BaseModel):
    status: str = Field(..., description="Trạng thái phản hồi (ok / ignored)")
    state: str = Field(..., description="Trạng thái FSM hiện tại")
    idle_seconds_remaining: float = Field(0.0, description="Số giây còn lại trước khi ngắt")
