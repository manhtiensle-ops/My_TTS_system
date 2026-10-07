"""
video_renderer.py — Bộ xử lý kết nối ảnh tĩnh và audio thành video MP4 bằng FFmpeg.
"""

import os
import subprocess


class StillImageVideoRenderer:
    """Bộ xử lý ghép nối 1 ảnh tĩnh + audio MP3/WAV thành video MP4 tối ưu cho YouTube."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def render_video(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        resolution: str = "1920x1080",
        fps: int = 1,
    ) -> str:
        """Thực thi ghép ảnh tĩnh với audio bằng FFmpeg.

        Args:
            image_path: Đường dẫn file ảnh tĩnh (JPG/PNG).
            audio_path: Đường dẫn file audio (MP3/WAV).
            output_path: Đường dẫn xuất file MP4 kết quả.
            resolution: Độ phân giải dạng "WIDTHxHEIGHT" (ví dụ "1920x1080").
            fps: Tỷ lệ khung hình (mặc định 1 fps cho ảnh tĩnh tối ưu dung lượng).

        Returns:
            Đường dẫn file video kết quả.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File ảnh bìa không tồn tại: {image_path}")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"File audio không tồn tại: {audio_path}")

        try:
            width, height = resolution.lower().split("x")
            width_val = int(width)
            height_val = int(height)
        except Exception:
            width_val, height_val = 1920, 1080

        # Lệnh FFmpeg still-image tối ưu
        vf_filter = (
            f"scale={width_val}:{height_val}:force_original_aspect_ratio=decrease,"
            f"pad={width_val}:{height_val}:(ow-iw)/2:(oh-ih)/2:color=black"
        )

        cmd = [
            self.ffmpeg_bin, "-y",
            "-loop", "1",
            "-framerate", str(fps),
            "-i", image_path,
            "-i", audio_path,
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg render video thất bại: {result.stderr}")

        return output_path
