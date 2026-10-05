from fastapi import APIRouter, Depends
from src.api.dependencies import get_engine
from src.engines.base import BaseTTSEngine
from src.schemas.voice import VoiceItem, VoicesResponse

router = APIRouter(prefix="/v1", tags=["Audio"])


@router.get("/voices", response_model=VoicesResponse)
async def list_voices(engine: BaseTTSEngine = Depends(get_engine)):
    """Lấy danh sách toàn bộ giọng đọc được hỗ trợ trên hệ thống."""
    raw_voices = engine.list_voices()
    items = [VoiceItem(**item) for item in raw_voices]
    return VoicesResponse(voices=items)
