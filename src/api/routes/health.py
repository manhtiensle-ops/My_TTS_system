from fastapi import APIRouter, Depends, Response, status
from src.api.dependencies import get_engine
from src.engines.base import BaseTTSEngine
from src.schemas.health import HealthResponse

router = APIRouter(tags=["Monitoring"])


@router.get("/health", response_model=HealthResponse)
async def health_check(engine: BaseTTSEngine = Depends(get_engine)):
    """Kiểm tra tình trạng sẵn sàng của server và bộ nhớ GPU VRAM."""
    is_cuda, device_name, vram_mb = engine.get_status()
    # Kiểm tra cờ is_loaded nếu có
    is_loaded = getattr(engine, "is_loaded", False)

    if not is_loaded:
        return Response(
            content='{"status": "loading", "model_loaded": false}',
            media_type="application/json",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return HealthResponse(
        status="ok",
        model_loaded=True,
        device=device_name,
        vram_used_mb=vram_mb,
    )
