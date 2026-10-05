"""
audio_concat.py — Bộ xử lý ghép nối và chuyển đổi âm thanh bằng FFmpeg.
"""

import os
import subprocess
import tempfile
from typing import List


class AudioConcatenator:
    """Bộ xử lý ghép nối danh sách file WAV thành một file duy nhất bằng FFmpeg demuxer."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def concat(self, wav_paths: List[str], output_path: str) -> str:
        """Nối danh sách file WAV theo thứ tự.

        Args:
            wav_paths: Danh sách đường dẫn file WAV cần nối (theo thứ tự tuần tự).
            output_path: Đường dẫn lưu file kết quả (.wav hoặc .mp3).

        Returns:
            Đường dẫn file kết quả sau khi ghép nối thành công.
        """
        if not wav_paths:
            raise ValueError("Danh sách file WAV rỗng, không thể ghép nối.")

        if len(wav_paths) == 1:
            self._convert_or_copy(wav_paths[0], output_path)
            return output_path

        filelist_fd, filelist_path = tempfile.mkstemp(suffix=".txt", prefix="tts_concat_")
        try:
            with os.fdopen(filelist_fd, "w", encoding="utf-8") as f:
                for p in wav_paths:
                    safe_path = p.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            is_mp3 = output_path.lower().endswith(".mp3")
            cmd = [
                self.ffmpeg_bin, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", filelist_path,
            ]

            if is_mp3:
                cmd += ["-b:a", "192k", output_path]
            else:
                # WAV nối bằng stream copy không qua re-encode (cực nhanh, không mất chất lượng)
                cmd += ["-c", "copy", output_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg concat thất bại: {result.stderr}")

            return output_path

        finally:
            if os.path.exists(filelist_path):
                os.unlink(filelist_path)

    def _convert_or_copy(self, input_path: str, output_path: str) -> None:
        """Sao chép hoặc chuyển định dạng cho trường hợp chỉ có 1 file."""
        is_mp3 = output_path.lower().endswith(".mp3")
        cmd = [self.ffmpeg_bin, "-y", "-i", input_path]
        if is_mp3:
            cmd += ["-b:a", "192k", output_path]
        else:
            cmd += ["-c", "copy", output_path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg convert thất bại: {result.stderr}")


# Hàm tiện ích cho tương thích ngược
def concat_wav_files(wav_paths: List[str], output_path: str) -> str:
    return AudioConcatenator().concat(wav_paths, output_path)
