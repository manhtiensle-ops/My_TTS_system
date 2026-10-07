"""
sorter.py — Natural Sorter cho danh sách file chapter.
"""

import re
from pathlib import Path
from typing import List, Union


class NaturalSorter:
    """Sắp xếp danh sách đường dẫn file theo thứ tự số tự nhiên (chap 1 -> chap 2 -> chap 10)."""

    @staticmethod
    def extract_chapter_number(filename_or_path: Union[str, Path]) -> float:
        """Bóc tách số thứ tự chương từ tên file.

        Ví dụ:
            'chap_1.txt'      -> 1.0
            'chap_2.txt'      -> 2.0
            'chap_10.txt'     -> 10.0
            'Chuong_10.5.txt' -> 10.5
        """
        name = Path(filename_or_path).name
        # Tìm cụm số đầu tiên (kể cả số thập phân)
        match = re.search(r"(\d+(?:\.\d+)?)", name)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 999999.0  # Nếu không thấy số, đẩy xuống cuối

    @classmethod
    def sort_files(cls, file_paths: List[Path]) -> List[Path]:
        """Trả về danh sách Path đã được sắp xếp theo thứ tự số tự nhiên."""
        return sorted(file_paths, key=cls.extract_chapter_number)
