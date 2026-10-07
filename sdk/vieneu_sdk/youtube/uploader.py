"""
uploader.py — Động cơ Resumable Upload MP4 lên YouTube kèm Exponential Backoff.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from vieneu_sdk.youtube.auth import YouTubeAuthManager
from vieneu_sdk.youtube.metadata import VideoMetadata
from vieneu_sdk.youtube.quota import QuotaTracker


@dataclass
class UploadResult:
    """Kết quả hoàn thành của tiến trình upload video YouTube."""
    video_id: str
    video_url: str
    thumbnail_uploaded: bool
    playlist_item_id: Optional[str] = None
    status: str = "uploaded"  # "uploaded" | "quota_exceeded" | "failed"


class YouTubeUploader:
    """Lớp xử lý tải video MP4 lên kênh YouTube."""

    def __init__(self, auth_manager: YouTubeAuthManager, quota_tracker: Optional[QuotaTracker] = None):
        self.auth = auth_manager
        self.quota = quota_tracker or QuotaTracker()

    def upload_video(
        self,
        video_path: Path,
        metadata: VideoMetadata,
        thumbnail_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> UploadResult:
        """Thực thi upload video lên YouTube theo phương thức Resumable Chunking."""
        if not video_path.exists():
            raise FileNotFoundError(f"File video không tồn tại: {video_path}")

        has_thumb = thumbnail_path is not None and thumbnail_path.exists()
        has_play = metadata.playlist_id is not None and bool(metadata.playlist_id.strip())

        if not self.quota.can_upload(has_thumbnail=has_thumb, has_playlist=has_play):
            print("⚠️ Hạn ngạch Quota YouTube trong ngày đã hết (10,000 units/ngày).")
            return UploadResult(
                video_id="",
                video_url="",
                thumbnail_uploaded=False,
                status="quota_exceeded",
            )

        from googleapiclient.http import MediaFileUpload

        service = self.auth.get_service()

        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": metadata.category_id,
            },
            "status": {
                "privacyStatus": metadata.privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        chunk_size = self.auth.config.chunk_size_bytes
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            chunksize=chunk_size,
            resumable=True,
        )

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        retry = 0
        max_retries = 8

        print(f"📡 Bắt đầu tải video lên YouTube: {metadata.title}")

        while response is None:
            try:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.progress() * 100.0)
            except Exception as e:
                retry += 1
                if retry > max_retries:
                    raise RuntimeError(f"Lỗi mạng kéo dài khi upload video: {e}")
                sleep_time = 2 ** retry
                print(f"⚠️ Gián đoạn kết nối. Thử lại lần {retry}/{max_retries} sau {sleep_time}s...")
                time.sleep(sleep_time)

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        self.quota.consume(QuotaTracker.UPLOAD_COST)
        print(f"✅ Video đã tải lên thành công: {video_url}")

        # Post-processing: Upload Thumbnail
        thumb_success = False
        if has_thumb:
            try:
                thumb_media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
                service.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                self.quota.consume(QuotaTracker.THUMBNAIL_COST)
                thumb_success = True
                print("🖼️ Đã cài đặt ảnh bìa Thumbnail thành công!")
            except Exception as e:
                print(f"⚠️ Lỗi khi cài ảnh Thumbnail: {e}")

        # Post-processing: Thêm vào Playlist
        playlist_item_id = None
        if has_play:
            try:
                playlist_body = {
                    "snippet": {
                        "playlistId": metadata.playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                }
                pl_res = service.playlistItems().insert(part="snippet", body=playlist_body).execute()
                playlist_item_id = pl_res.get("id")
                self.quota.consume(QuotaTracker.PLAYLIST_COST)
                print(f"📋 Đã thêm video vào Playlist {metadata.playlist_id}")
            except Exception as e:
                print(f"⚠️ Lỗi khi thêm video vào Playlist: {e}")

        return UploadResult(
            video_id=video_id,
            video_url=video_url,
            thumbnail_uploaded=thumb_success,
            playlist_item_id=playlist_item_id,
            status="uploaded",
        )
