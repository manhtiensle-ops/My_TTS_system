"""
audio_concat.py — Nối danh sách file WAV thành 1 file duy nhất bằng ffmpeg.
"""

import os
import subprocess
import tempfile


def concat_wav_files(wav_paths: list[str], output_path: str) -> str:
    """
    Nối nhiều file WAV thành 1 file WAV hoặc MP3 bằng ffmpeg concat demuxer.

    Args:
        wav_paths: Danh sách đường dẫn tuyệt đối các file WAV cần nối (đúng thứ tự)
        output_path: Đường dẫn file output (.wav hoặc .mp3)

    Returns:
        Đường dẫn file output đã tạo
    """
    if not wav_paths:
        raise ValueError("Danh sách file WAV rỗng")

    if len(wav_paths) == 1:
        # Chỉ có 1 file → copy hoặc convert trực tiếp
        _ffmpeg_single(wav_paths[0], output_path)
        return output_path

    # Tạo file danh sách concat tạm
    filelist_fd, filelist_path = tempfile.mkstemp(suffix=".txt", prefix="tts_concat_")
    try:
        with os.fdopen(filelist_fd, "w") as f:
            for p in wav_paths:
                # Escape dấu nháy đơn trong đường dẫn
                safe = p.replace("'", "'\\''")
                f.write(f"file '{safe}'\n")

        is_mp3 = output_path.lower().endswith(".mp3")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", filelist_path,
        ]

        if is_mp3:
            cmd += ["-b:a", "192k", output_path]
        else:
            # WAV → copy codec (rất nhanh, không re-encode)
            cmd += ["-c", "copy", output_path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat thất bại: {result.stderr}")

        return output_path

    finally:
        os.unlink(filelist_path)


def _ffmpeg_single(input_path: str, output_path: str) -> None:
    """Convert hoặc copy 1 file đơn lẻ."""
    is_mp3 = output_path.lower().endswith(".mp3")

    if is_mp3:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-b:a", "192k", output_path]
    else:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg convert thất bại: {result.stderr}")
