from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_novel_service
from src.lifecycle.states import StateTransitionError
from src.schemas.novel import NovelRequest
from src.services.novel_service import NovelPipelineService

router = APIRouter(prefix="/v1", tags=["Novel"])


@router.post("/audio/novel")
async def generate_novel_audio(
    request: NovelRequest,
    novel_service: NovelPipelineService = Depends(get_novel_service),
):
    """Pipeline tự động xử lý audio cho truyện tiểu thuyết dài."""
    voice = request.voice or "Ngọc Huyền"
    try:
        result = await novel_service.process_novel(
            text=request.input,
            voice_name=voice,
            speed=request.speed or 1.2,
            response_format=request.response_format or "wav",
            chapter_name=request.chapter_name or "",
            target_words=request.target_words or 100,
        )
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý truyện dài: {str(e)}",
        )

    return Response(
        content=result.audio_bytes,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-TTS-Chunks": str(result.total_chunks),
        },
    )
