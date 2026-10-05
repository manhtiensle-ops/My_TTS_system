from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_engine, get_novel_service
from src.engines.base import BaseTTSEngine
from src.schemas.novel import NovelRequest
from src.services.novel_service import NovelPipelineService

router = APIRouter(prefix="/v1", tags=["Novel"])


@router.post("/audio/novel")
async def generate_novel_audio(
    request: NovelRequest,
    engine: BaseTTSEngine = Depends(get_engine),
    novel_service: NovelPipelineService = Depends(get_novel_service),
):
    """Pipeline tự động xử lý audio cho truyện tiểu thuyết dài.
    
    1. Kiểm tra tính hợp lệ của giọng đọc (mặc định 'Ngọc Huyền', tốc độ 1.2).
    2. Tự động chia nhỏ văn bản thành các đoạn ~100-200 từ theo dấu '\\n'.
    3. Chạy inference trên GPU cho từng đoạn.
    4. Dùng FFmpeg ghép nối thành file hoàn chỉnh và trả về client.
    """
    canonical_voice = engine.resolve_voice(request.voice)
    if not canonical_voice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Voice '{request.voice}' không tồn tại. Dùng GET /v1/voices để xem danh sách.",
        )

    try:
        result = await novel_service.process_novel(
            text=request.input,
            voice_name=canonical_voice,
            speed=request.speed,
            response_format=request.response_format,
            chapter_name=request.chapter_name,
            target_words=request.target_words,
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
