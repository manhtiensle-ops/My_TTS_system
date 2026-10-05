from typing import Optional
from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    """Request body cho POST /v1/audio/speech (luồng Video Shorts / TikTok)."""
    input: str = Field(..., min_length=1, description="Nội dung văn bản tiếng Việt cần đọc")
    voice: str = Field(default="Trúc Ly", description="Tên hoặc mã nhận dạng giọng đọc (ví dụ: 'Trúc Ly', 'truc_ly')")
    model: Optional[str] = Field(default="v3turbo", description="Phiên bản mô hình TTS")
    response_format: Optional[str] = Field(default="wav", pattern="^(wav|mp3)$", description="Định dạng âm thanh đầu ra")
    speed: Optional[float] = Field(default=1.1, ge=0.5, le=2.0, description="Tốc độ đọc (mặc định 1.1 cho Video Shorts)")
