import io
import threading
from typing import Tuple, List, Dict, Optional

import soundfile as sf
import torch

from .base import BaseTTSEngine


class VieNeuEngine(BaseTTSEngine):
    """Engine triển khai cho mô hình VieNeu-TTS v3 Turbo, hỗ trợ tăng tốc CUDA."""

    VOICE_METADATA: List[Dict[str, str]] = [
        {"id": "ngoc_huyen", "name": "Ngọc Huyền", "gender": "female", "region": "North"},
        {"id": "pham_tuyen", "name": "Phạm Tuyên", "gender": "male", "region": "North"},
        {"id": "mai_anh", "name": "Mai Anh", "gender": "female", "region": "North"},
        {"id": "minh_quan_pro", "name": "Minh Quân Pro", "gender": "male", "region": "North"},
        {"id": "quang_son", "name": "Quang Sơn", "gender": "male", "region": "Central"},
        {"id": "ngoc_tran", "name": "Ngọc Trân", "gender": "female", "region": "Central"},
        {"id": "thai_son", "name": "Thái Sơn", "gender": "male", "region": "South"},
        {"id": "thuy_dung", "name": "Thùy Dung", "gender": "female", "region": "South"},
        {"id": "adam_bua", "name": "Adam bựa", "gender": "male", "region": "South"},
        {"id": "truc_ly", "name": "Trúc Ly", "gender": "female", "region": "South"},
    ]

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.tts = None
        self.is_loaded: bool = False
        self._lock = threading.Lock()
        self._voice_alias_map: Dict[str, str] = {}
        self._build_voice_map()

    def _build_voice_map(self) -> None:
        """Xây dựng bảng tra cứu voice hỗ trợ cả ID viết liền và Tên hiển thị."""
        for v in self.VOICE_METADATA:
            self._voice_alias_map[v["id"].lower()] = v["name"]
            self._voice_alias_map[v["name"].lower()] = v["name"]

    def load_model(self) -> None:
        """Nạp trọng số mô hình lên VRAM và kích hoạt CUDA Graphs."""
        with self._lock:
            if self.is_loaded:
                return

            # Import vieneu động để tránh tải lúc import engine
            from vieneu import Vieneu

            self.tts = Vieneu()

            # Chạy thử 1 câu ngắn để compile và capture CUDA Graph vào GPU
            if torch.cuda.is_available():
                _ = self.tts.infer("Khởi động hệ thống.", voice="Ngọc Huyền")
                torch.cuda.synchronize()

            self.is_loaded = True

    def get_status(self) -> Tuple[bool, str, float]:
        """Đọc dung lượng VRAM thực tế từ Driver NVIDIA."""
        if not torch.cuda.is_available():
            return False, "cpu", 0.0

        device_name = torch.cuda.get_device_name(0)
        vram_bytes = torch.cuda.memory_allocated(0)
        vram_mb = round(vram_bytes / (1024 * 1024), 2)
        return True, device_name, vram_mb

    def get_cuda_status(self) -> Tuple[bool, str, float]:
        """Alias tương thích ngược."""
        return self.get_status()

    def resolve_voice(self, voice_input: str) -> Optional[str]:
        """Chuẩn hóa ID giọng nói truyền từ client thành tên Voice chuẩn."""
        return self._voice_alias_map.get(voice_input.strip().lower())

    def list_voices(self) -> List[Dict[str, str]]:
        """Lấy danh sách các giọng đọc hỗ trợ."""
        return self.VOICE_METADATA

    def synthesize(
        self,
        text: str,
        voice_name: str,
        speed: float = 1.0,
        response_format: str = "wav",
    ) -> bytes:
        """Thực thi inference song song và mã hóa output thành binary stream."""
        if not self.is_loaded or self.tts is None:
            raise RuntimeError("Mô hình chưa được nạp vào bộ nhớ GPU.")

        with self._lock:
            audio_array = self.tts.infer(
                text=text,
                voice=voice_name,
                speed=speed,
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()

        buffer = io.BytesIO()
        if response_format == "wav":
            sf.write(buffer, audio_array, self.sample_rate, format="WAV", subtype="PCM_16")
        elif response_format == "mp3":
            sf.write(buffer, audio_array, self.sample_rate, format="MP3")
        else:
            raise ValueError(f"Định dạng '{response_format}' không được hỗ trợ (chỉ nhận 'wav' hoặc 'mp3').")

        return buffer.getvalue()

    def unload_model(self) -> None:
        """Dọn dẹp VRAM khi tắt server."""
        with self._lock:
            if self.tts is not None:
                del self.tts
                self.tts = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self.is_loaded = False
