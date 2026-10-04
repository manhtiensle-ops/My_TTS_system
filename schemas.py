from typing import Optional, List
from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    """Request body cho POST /v1/audio/speech (video Shorts)."""
    input: str = Field(..., min_length=1, description="Nội dung văn bản tiếng Việt cần đọc")
    voice: str = Field(..., description="Tên hoặc mã nhận dạng giọng đọc (ví dụ: 'Trúc Ly', 'truc_ly')")
    model: Optional[str] = Field(default="v3turbo", description="Phiên bản mô hình TTS")
    response_format: Optional[str] = Field(default="wav", pattern="^(wav|mp3)$", description="Định dạng âm thanh đầu ra")
    speed: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="Tốc độ đọc (từ 0.5 đến 2.0)")


class NovelRequest(BaseModel):
    """Request body cho POST /v1/audio/novel (truyện tiểu thuyết dài)."""
    input: str = Field(..., min_length=1, description="Toàn bộ nội dung chapter truyện")
    voice: str = Field(default="Ngọc Huyền", description="Giọng đọc truyện")
    speed: float = Field(default=1.2, ge=0.5, le=2.0, description="Tốc độ đọc")
    response_format: str = Field(default="wav", pattern="^(wav|mp3)$", description="Định dạng audio đầu ra")
    chapter_name: str = Field(default="", description="Tên chapter (tuỳ chọn, dùng đặt tên file)")
    target_words: int = Field(default=100, ge=20, le=500, description="Số từ tối thiểu trước khi cắt đoạn tại dấu xuống dòng")


class VoiceItem(BaseModel):
    id: str
    name: str
    gender: str
    region: str


class VoicesResponse(BaseModel):
    voices: List[VoiceItem]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: Optional[str] = None
    vram_used_mb: Optional[float] = None
