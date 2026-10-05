from typing import List
from pydantic import BaseModel


class VoiceItem(BaseModel):
    """Thông tin chi tiết của một giọng đọc."""
    id: str
    name: str
    gender: str
    region: str


class VoicesResponse(BaseModel):
    """Danh sách tất cả các giọng đọc được hỗ trợ."""
    voices: List[VoiceItem]
