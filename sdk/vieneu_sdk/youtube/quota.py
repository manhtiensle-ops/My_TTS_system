"""
quota.py — Quản lý hạn ngạch 10,000 units/ngày cho YouTube Data API v3.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


class QuotaTracker:
    """Theo dõi và bảo vệ hạn ngạch API YouTube."""

    UPLOAD_COST: int = 1600
    THUMBNAIL_COST: int = 50
    PLAYLIST_COST: int = 50
    DAILY_LIMIT: int = 10000

    def __init__(self, cache_file: Path = Path.home() / ".vieneu" / "youtube_quota.json"):
        self.cache_file = cache_file

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load_data(self) -> Dict[str, Any]:
        if not self.cache_file.exists():
            return {"date": self._today_utc(), "used_units": 0}
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            if data.get("date") != self._today_utc():
                return {"date": self._today_utc(), "used_units": 0}
            return data
        except Exception:
            return {"date": self._today_utc(), "used_units": 0}

    def _save_data(self, data: Dict[str, Any]) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def can_upload(self, has_thumbnail: bool = True, has_playlist: bool = True) -> bool:
        """Kiểm tra xem còn đủ Quota để upload video hay không."""
        needed = self.UPLOAD_COST
        if has_thumbnail:
            needed += self.THUMBNAIL_COST
        if has_playlist:
            needed += self.PLAYLIST_COST

        data = self._load_data()
        return (data.get("used_units", 0) + needed) <= self.DAILY_LIMIT

    def consume(self, units: int) -> None:
        """Cộng dồn số units đã sử dụng vào cache."""
        data = self._load_data()
        data["used_units"] = data.get("used_units", 0) + units
        self._save_data(data)

    def get_remaining_slots(self) -> int:
        """Trả về số video còn có thể upload trong ngày."""
        data = self._load_data()
        rem = self.DAILY_LIMIT - data.get("used_units", 0)
        single_cost = self.UPLOAD_COST + self.THUMBNAIL_COST + self.PLAYLIST_COST
        return max(0, rem // single_cost)
