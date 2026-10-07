import urllib.parse
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from src.api.dependencies import get_novel_video_service
from src.services.novel_video_service import NovelVideoService

router = APIRouter(prefix="/v1/video", tags=["Novel Video Pipeline"])


@router.post("/novel")
async def render_novel_video(
    text: str = Form(..., description="Nội dung chapter"),
    chapter_name: str = Form("", description="Tên chapter"),
    voice: str = Form("Ngọc Huyền", description="Giọng đọc"),
    speed: float = Form(1.2, description="Tốc độ"),
    resolution: str = Form("1920x1080", description="Độ phân giải"),
    target_words: int = Form(100, description="Số từ mỗi chunk"),
    cover_image: UploadFile = File(..., description="Ảnh bìa tĩnh (JPG/PNG)"),
    video_service: NovelVideoService = Depends(get_novel_video_service),
):
    """Endpoint xử lý chuyển đổi chapter truyện + ảnh bìa thành file MP4 chuẩn YouTube."""
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung text chapter không được để rỗng.",
        )

    cover_bytes = await cover_image.read()
    if not cover_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File ảnh bìa tải lên rỗng.",
        )

    try:
        result = await video_service.process_novel_video(
            text=text,
            cover_bytes=cover_bytes,
            cover_filename=cover_image.filename or "cover.jpg",
            voice_name=voice,
            speed=speed,
            chapter_name=chapter_name,
            resolution=resolution,
            target_words=target_words,
        )

        encoded_filename = urllib.parse.quote(result.filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        }

        return Response(
            content=result.video_bytes,
            media_type=result.media_type,
            headers=headers,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi render video: {str(e)}",
        )
