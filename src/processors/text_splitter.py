"""
text_splitter.py — Bộ phân tách văn bản truyện dài theo thuật toán ngắt dòng thông minh.
"""

from typing import List


class NovelTextSplitter:
    """Bộ chia nhỏ văn bản truyện tiểu thuyết dài thành từng đoạn ~100-200 từ.

    Quy tắc ngắt đoạn:
    1. Tách văn bản thành các dòng theo ký tự xuống dòng '\\n'.
    2. Duyệt từng dòng và cộng dồn số lượng từ thực tế.
    3. Khi số từ tích lũy đạt hoặc vượt ngưỡng target_words (mặc định 100 từ),
       ngắt đoạn ngay tại ký tự '\\n' này để đảm bảo không bị đứt câu nói dở.
    4. Đoạn văn bản cuối cùng gom toàn bộ phần dư còn lại.
    """

    def __init__(self, default_target_words: int = 100):
        self.default_target_words = default_target_words

    def split(self, text: str, target_words: int = None) -> List[str]:
        """Chia văn bản thành danh sách các đoạn nhỏ.

        Args:
            text: Nội dung toàn bộ chapter truyện.
            target_words: Ngưỡng từ tối thiểu để ngắt đoạn (mặc định lấy từ cấu hình).

        Returns:
            Danh sách các chuỗi văn bản đã được phân tách.
        """
        threshold = target_words if target_words is not None else self.default_target_words
        lines = text.split("\n")
        chunks: List[str] = []
        current_lines: List[str] = []
        word_count = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Giữ dòng trống để duy trì ngắt nhịp tự nhiên nhưng không tính từ
                current_lines.append(line)
                continue

            current_lines.append(line)
            word_count += len(stripped.split())

            if word_count >= threshold:
                chunk_text = "\n".join(current_lines).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                current_lines = []
                word_count = 0

        # Xử lý phần còn lại sau khi duyệt hết các dòng
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(chunk_text)

        return chunks


# Hàm tiện ích cho tương thích ngược
def split_chapter(text: str, target_words: int = 100) -> List[str]:
    return NovelTextSplitter(default_target_words=target_words).split(text)
