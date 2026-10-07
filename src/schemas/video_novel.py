from pydantic import BaseModel, Field


class NovelVideoRequest(BaseModel):
    """Schema Pydantic cho tham số render video truyện."""
    text: str = Field(..., min_length=1, description="Nội dung văn bản chapter truyện")
    chapter_name: str = Field(default="", description="Tên chapter truyện")
    voice: str = Field(default="Ngọc Huyền", description="Giọng đọc tiểu thuyết")
    speed: float = Field(default=1.2, ge=0.5, le=2.0, description="Tốc độ đọc")
    target_words: int = Field(default=100, ge=20, le=500, description="Số từ mỗi đoạn")
    resolution: str = Field(default="1920x1080", description="Tỷ lệ khung hình video")
