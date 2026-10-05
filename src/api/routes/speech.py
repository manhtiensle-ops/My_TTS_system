import asyncio
from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_engine
from src.engines.base import BaseTTSEngine
from src.schemas.speech import SpeechRequest

router = APIRouter(prefix="/v1", tags=["Audio"])


@router.post("/audio/speech")
async def generate_speech(
    request: SpeechRequest,
    engine: BaseTTSEngine = Depends(get_engine),
):
    """Tổng hợp giọng nói cho các đoạn ngắn (Shorts, TikTok, YouTube Video)."""
    canonical_voice = engine.resolve_voice(request.voice)
    if not canonical_voice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Voice '{request.voice}' không tồn tại. Dùng GET /v1/voices để xem danh sách.",
        )

    try:
        audio_bytes = await asyncio.to_thread(
            engine.synthesize,
            text=request.input,
            voice_name=canonical_voice,
            speed=request.speed or 1.1,
            response_format=request.response_format or "wav",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference thất bại: {str(e)}",
        )

    fmt = request.response_format or "wav"
    media_type = "audio/wav" if fmt == "wav" else "audio/mpeg"

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="speech.{fmt}"'
        },
    )
