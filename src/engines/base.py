from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple


class BaseTTSEngine(ABC):
    """Giao diện trừu tượng chuẩn (Abstract Base Class) cho các TTS Engine."""

    @abstractmethod
    def load_model(self) -> None:
        """Nạp trọng số mô hình lên bộ nhớ (GPU VRAM / RAM)."""
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Dọn dẹp và giải phóng tài nguyên bộ nhớ."""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_name: str,
        speed: float = 1.0,
        response_format: str = "wav",
    ) -> bytes:
        """Tổng hợp văn bản thành mảng nhị phân âm thanh (WAV hoặc MP3)."""
        pass

    @abstractmethod
    def resolve_voice(self, voice_input: str) -> Optional[str]:
        """Chuẩn hóa ID giọng nói hoặc tên nhập từ client thành tên chuẩn của Engine."""
        pass

    @abstractmethod
    def get_status(self) -> Tuple[bool, str, float]:
        """Trả về trạng thái phần cứng (is_cuda, device_name, vram_used_mb)."""
        pass

    @abstractmethod
    def list_voices(self) -> List[Dict[str, str]]:
        """Lấy danh sách thông tin metadata của tất cả các giọng đọc hỗ trợ."""
        pass
