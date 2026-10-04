"""
text_splitter.py — Chia nhỏ văn bản dài thành các đoạn ~100-200 từ.

Thuật toán:
  1. Tách text thành danh sách dòng theo '\n'
  2. Duyệt từng dòng, cộng dồn số từ
  3. Khi đếm được >= target_words → cắt tại '\n' này, bắt đầu đoạn mới
  4. Đoạn cuối gom phần còn lại
"""


def split_chapter(text: str, target_words: int = 100) -> list[str]:
    """
    Chia text dài thành danh sách đoạn nhỏ.

    Args:
        text: Toàn bộ nội dung chapter (có thể rất dài)
        target_words: Số từ tối thiểu trước khi cắt tại '\n' tiếp theo

    Returns:
        Danh sách các đoạn text, mỗi đoạn ~100-200 từ
    """
    lines = text.split("\n")
    chunks: list[str] = []
    current_lines: list[str] = []
    word_count = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Giữ dòng trống trong đoạn hiện tại (không đếm từ)
            current_lines.append(line)
            continue

        current_lines.append(line)
        word_count += len(stripped.split())

        if word_count >= target_words:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(chunk_text)
            current_lines = []
            word_count = 0

    # Đoạn cuối cùng (phần còn lại chưa đủ target_words)
    if current_lines:
        chunk_text = "\n".join(current_lines).strip()
        if chunk_text:
            chunks.append(chunk_text)

    return chunks
