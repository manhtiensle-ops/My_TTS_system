from typing import Optional
from pydantic import BaseModel, Field


class NovelRequest(BaseModel):
    """Request body cho POST /v1/audio/novel (luồng truyện tiểu thuyết dài)."""
    input: str = Field(..., min_length=1, description="Toàn bộ nội dung chapter truyện cần đọc")
    voice: str = Field(default="Ngọc Huyền", description="Giọng đọc truyện (mặc định 'Ngọc Huyền')")
    speed: float = Field(default=1.2, ge=0.5, le=2.0, description="Tốc độ đọc truyện (mặc định 1.2)")
    response_format: str = Field(default="wav", pattern="^(wav|mp3)$", description="Định dạng audio đầu ra (wav hoặc mp3)")
    chapter_name: str = Field(default="", description="Tên chapter truyện (tùy chọn, dùng đặt tên file audio tải về)")
    target_words: int = Field(default=100, ge=20, le=500, description="Số từ tối thiểu trước khi cắt đoạn tại dấu xuống dòng '\\n'")
