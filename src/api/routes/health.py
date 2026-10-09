from fastapi import APIRouter
from src.lifecycle.supervisor import get_supervisor
from src.schemas.health import HealthResponse

router = APIRouter(tags=["Monitoring"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Kiểm tra tình trạng sẵn sàng của server và bộ nhớ GPU VRAM."""
    supervisor = get_supervisor()
    status_info = await supervisor.get_status()

    is_loaded = status_info["state"] in ("READY", "PROCESSING")
    status_str = "ok" if is_loaded else status_info["state"].lower()

    return HealthResponse(
        status=status_str,
        model_loaded=is_loaded,
        device=status_info.get("device", "cuda"),
        vram_used_mb=status_info.get("vram_allocated_mb", 0.0),
    )
