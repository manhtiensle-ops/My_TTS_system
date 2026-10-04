from typing import Optional, List
from pydantic import BaseModel, Field

class SpeechRequest(BaseModel):
    input: str = Field(..., min_length=1, description="Nội dung văn bản tiếng Việt cần đọc")
    voice: str = Field(..., description="Tên hoặc mã nhận dạng giọng đọc (ví dụ: 'Ngọc Huyền', 'ngoc_huyen')")
    model: Optional[str] = Field(default="v3turbo", description="Phiên bản mô hình TTS")
    response_format: Optional[str] = Field(default="wav", pattern="^(wav|mp3)$", description="Định dạng âm thanh đầu ra")
    speed: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="Tốc độ đọc (từ 0.5 đến 2.0)")

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