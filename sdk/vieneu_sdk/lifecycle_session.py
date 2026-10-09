from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from vieneu_sdk.client import VieneuClient


class GPUSession:
    """
    Context Manager cho phép Hermes Animator hoặc Client script làm chủ 100% vòng đời VRAM GPU.
    Tự động gửi lệnh nạp GPU khi bắt đầu khối `with` và tự động rút VRAM về 0 MB khi thoát.
    """

    def __init__(
        self,
        client: "VieneuClient",
        model_name: str = "v3turbo",
        voice_preload: Optional[List[str]] = None,
        idle_timeout_seconds: int = 600,
        auto_unload: bool = True,
    ):
        self.client = client
        self.model_name = model_name
        self.voice_preload = voice_preload or ["ngoc_huyen", "truc_ly"]
        self.idle_timeout_seconds = idle_timeout_seconds
        self.auto_unload = auto_unload

    def __enter__(self):
        self.client.load_gpu(
            model_name=self.model_name,
            voice_preload=self.voice_preload,
            idle_timeout_seconds=self.idle_timeout_seconds,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.auto_unload:
            try:
                self.client.unload_gpu(force=False)
            except Exception as e:
                print(f"[GPUSession] Notice: Exception during auto-unload: {e}")
