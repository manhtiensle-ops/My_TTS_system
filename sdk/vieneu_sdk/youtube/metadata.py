"""
metadata.py — Định dạng metadata video chuẩn SEO cho YouTube.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    """Mô hình dữ liệu metadata đăng tải video YouTube."""

    title: str = Field(..., max_length=100, description="Tiêu đề video (<= 100 ký tự)")
    description: str = Field(..., description="Mô tả video")
    tags: List[str] = Field(default_factory=list, description="Thẻ từ khóa SEO")
    category_id: str = Field(default="24", description="Danh mục YouTube (24 = Entertainment)")
    privacy_status: str = Field(default="unlisted", description="private | unlisted | public")
    playlist_id: Optional[str] = Field(default=None, description="ID Playlist tự động thêm")


class NovelMetadataBuilder:
    """Bộ tạo metadata tự động cho truyện audio/video."""

    def __init__(
        self,
        novel_title: str,
        author: str = "Tác giả",
        voice_actor: str = "Ngọc Huyền (VieNeu-TTS v3)",
        channel_name: str = "Kênh Truyện Audio Hay",
    ):
        self.novel_title = novel_title
        self.author = author
        self.voice_actor = voice_actor
        self.channel_name = channel_name

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[-\s]+", "", text)

    def build_for_chapter(
        self,
        chapter_name: str,
        chapter_number: Optional[float] = None,
        privacy: str = "unlisted",
        playlist_id: Optional[str] = None,
        custom_tags: Optional[List[str]] = None,
    ) -> VideoMetadata:
        """Tạo đối tượng VideoMetadata hoàn chỉnh cho 1 chapter."""
        chap_str = f"Tập {int(chapter_number)}: " if chapter_number is not None else ""
        raw_title = f"{self.novel_title} - {chap_str}{chapter_name} | Truyện Audio Tiên Hiệp Hay"

        # Cắt tiêu đề nếu quá 100 ký tự
        if len(raw_title) > 100:
            title = raw_title[:97] + "..."
        else:
            title = raw_title

        desc_lines = [
            f"🎧 {self.novel_title.upper()} - {chap_str}{chapter_name}",
            f"✍️ Tác giả: {self.author}",
            f"🎙️ Giọng đọc AI: {self.voice_actor}",
            f"📺 Phát trên kênh: {self.channel_name}",
            "",
            "----------------------------------------",
            "📖 Tóm tắt nội dung:",
            f"Chào mừng bạn đến với bộ truyện {self.novel_title}. Hãy đăng ký kênh để theo dõi các tập mới nhất!",
            "",
            "⚠️ Bản quyền thuộc về kênh. Vui lòng không reup.",
            "----------------------------------------",
            f"#truyenaudio #tienhiep #{self._slugify(self.novel_title)} #vieneu",
        ]
        description = "\n".join(desc_lines)

        tags = [
            "truyện audio",
            self.novel_title,
            "tiên hiệp",
            "truyện audio tiên hiệp",
            "audiobook",
            "vieneu tts",
        ]
        if custom_tags:
            tags.extend(custom_tags)

        return VideoMetadata(
            title=title,
            description=description,
            tags=tags[:15],
            category_id="24",
            privacy_status=privacy,
            playlist_id=playlist_id,
        )
