"""
config.py — Quản lý cấu hình biến môi trường cho YouTube API v3.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class YouTubeConfig(BaseModel):
    """Configuration cho YouTube Data API v3 xác thực OAuth2."""

    client_id: str = Field(..., description="OAuth2 Client ID")
    client_secret: str = Field(..., description="OAuth2 Client Secret")
    redirect_uri: str = Field(default="http://localhost:8080/", description="Redirect URI")
    token_cache_path: Path = Field(
        default=Path.home() / ".vieneu" / "youtube_token.json",
        description="Đường dẫn lưu file refresh token cache",
    )
    default_privacy: str = Field(default="unlisted", description="Quyền riêng tư: private | unlisted | public")
    default_category_id: str = Field(default="24", description="Mã danh mục YouTube (24 = Entertainment)")
    chunk_size_bytes: int = Field(default=8 * 1024 * 1024, description="Kích thước chunk upload 8MB")

    @classmethod
    def from_env(cls, env_path: Optional[Path] = None) -> "YouTubeConfig":
        """Load cấu hình từ biến môi trường hoặc file .env."""
        if env_path and env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)
        else:
            from dotenv import load_dotenv
            load_dotenv()

        client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            raise ValueError(
                "Thiếu YOUTUBE_CLIENT_ID hoặc YOUTUBE_CLIENT_SECRET trong môi trường/file .env"
            )

        token_cache_str = os.getenv("YOUTUBE_TOKEN_CACHE_FILE")
        token_cache_path = (
            Path(token_cache_str) if token_cache_str else Path.home() / ".vieneu" / "youtube_token.json"
        )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8080/"),
            token_cache_path=token_cache_path,
            default_privacy=os.getenv("YOUTUBE_DEFAULT_PRIVACY", "unlisted"),
            default_category_id=os.getenv("YOUTUBE_DEFAULT_CATEGORY_ID", "24"),
        )
