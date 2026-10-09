from fastapi import APIRouter, HTTPException, status

from src.lifecycle.supervisor import get_supervisor
from src.lifecycle.states import StateTransitionError
from src.schemas.lifecycle import (
    LoadModelRequest,
    UnloadModelRequest,
    LifecycleStatusResponse,
    HeartbeatRequest,
    HeartbeatResponse,
)

router = APIRouter(prefix="/v1/lifecycle", tags=["Lifecycle Controller"])


@router.post("/load", status_code=status.HTTP_200_OK)
async def load_model(req: LoadModelRequest = LoadModelRequest(model_name="v3turbo")):
    """
    Nạp mô hình VieNeu-TTS lên VRAM GPU (Animator Master Command).
    """
    supervisor = get_supervisor()
    try:
        res = await supervisor.load_model(
            model_name=req.model_name,
            voice_preload=req.voice_preload,
            idle_timeout_seconds=req.idle_timeout_seconds,
        )
        return res
    except StateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load model: {str(e)}",
        )


@router.post("/unload", status_code=status.HTTP_200_OK)
async def unload_model(req: UnloadModelRequest = UnloadModelRequest(force=False)):
    """
    Thu hồi 100% bộ nhớ VRAM GPU về 0 MB tức thì.
    """
    supervisor = get_supervisor()
    try:
        res = await supervisor.unload_model(force=req.force)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unload model: {str(e)}",
        )


@router.get("/status", response_model=LifecycleStatusResponse)
async def get_status():
    """
    Truy vấn trạng thái FSM hiện tại, VRAM allocated và bộ đếm thời gian Idle Watchdog.
    """
    supervisor = get_supervisor()
    status_info = await supervisor.get_status()
    return status_info


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(req: HeartbeatRequest = HeartbeatRequest(idle_timeout_seconds=None)):
    """
    Gia hạn phiên làm việc GPU, đặt lại đồng hồ đếm ngược Idle Watchdog.
    """
    supervisor = get_supervisor()
    res = await supervisor.heartbeat(idle_timeout_seconds=req.idle_timeout_seconds)
    return res
