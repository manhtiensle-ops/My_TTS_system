from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema trạng thái hoạt động của server và GPU VRAM."""
    status: str
    model_loaded: bool
    device: Optional[str] = None
    vram_used_mb: Optional[float] = None
