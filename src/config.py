import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Cấu hình toàn hệ thống TTS, đọc linh hoạt từ biến môi trường."""
    
    # Server network
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "7865"))
    
    # Storage & cache
    TMP_DIR: str = os.getenv("TTS_TMP_DIR", "/tmp")
    
    # Audio settings
    SAMPLE_RATE: int = int(os.getenv("TTS_SAMPLE_RATE", "48000"))
    
    # Default presets
    # 1. Video Shorts / TikTok / Reels: Trúc Ly (speed 1.1)
    DEFAULT_VOICE_SHORT: str = os.getenv("DEFAULT_VOICE_SHORT", "Trúc Ly")
    DEFAULT_SPEED_SHORT: float = float(os.getenv("DEFAULT_SPEED_SHORT", "1.1"))
    
    # 2. Truyện tiểu thuyết / Audiobooks: Ngọc Huyền (speed 1.2)
    DEFAULT_VOICE_NOVEL: str = os.getenv("DEFAULT_VOICE_NOVEL", "Ngọc Huyền")
    DEFAULT_SPEED_NOVEL: float = float(os.getenv("DEFAULT_SPEED_NOVEL", "1.2"))
    
    # Text splitting config
    DEFAULT_TARGET_WORDS: int = int(os.getenv("DEFAULT_TARGET_WORDS", "100"))


settings = Settings()
