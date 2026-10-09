from fastapi import APIRouter, HTTPException, Response, status

from src.lifecycle.supervisor import get_supervisor
from src.lifecycle.states import StateTransitionError
from src.schemas.speech import SpeechRequest

router = APIRouter(prefix="/v1", tags=["Audio"])


@router.post("/audio/speech")
async def generate_speech(request: SpeechRequest):
    """Tổng hợp giọng nói cho các đoạn ngắn (Shorts, TikTok, YouTube Video)."""
    supervisor = get_supervisor()
    try:
        audio_bytes = await supervisor.synthesize(
            text=request.input,
            voice=request.voice,
            speed=request.speed or 1.1,
            response_format=request.response_format or "wav",
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
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
        headers={"Content-Disposition": f'attachment; filename="speech.{fmt}"'},
    )
