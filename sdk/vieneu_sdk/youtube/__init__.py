"""
vieneu_sdk.youtube — Package hỗ trợ tự động đăng video YouTube API v3.
"""

from vieneu_sdk.youtube.config import YouTubeConfig
from vieneu_sdk.youtube.auth import YouTubeAuthManager
from vieneu_sdk.youtube.quota import QuotaTracker
from vieneu_sdk.youtube.metadata import VideoMetadata, NovelMetadataBuilder
from vieneu_sdk.youtube.uploader import YouTubeUploader, UploadResult

__all__ = [
    "YouTubeConfig",
    "YouTubeAuthManager",
    "QuotaTracker",
    "VideoMetadata",
    "NovelMetadataBuilder",
    "YouTubeUploader",
    "UploadResult",
]
