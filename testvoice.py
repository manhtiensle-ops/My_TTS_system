import os
import time
from pathlib import Path
from typing import Dict, Any, List
import requests

class TTSClient:
    """Client giao tiếp với máy chủ TTS chuẩn OpenAI."""

    def __init__(self, base_url: str = "http://127.0.0.1:7865"):
        self.base_url = base_url.rstrip("/")

    def check_health(self) -> Dict[str, Any]:
        """Kiểm tra trạng thái server và mức tiêu thụ VRAM."""
        response = requests.get(f"{self.base_url}/health", timeout=10)
        response.raise_for_status()
        return response.json()

    def get_available_voices(self) -> List[Dict[str, str]]:
        """Gọi API lấy toàn bộ danh sách voice metadata."""
        response = requests.get(f"{self.base_url}/v1/voices", timeout=10)
        response.raise_for_status()
        return response.json().get("voices", [])

    def generate_speech(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        response_format: str = "wav",
        output_file: str = "result.wav"
    ) -> float:
        """Gửi request tổng hợp giọng nói và ghi nhị phân ra đĩa cứng."""
        payload = {
            "input": text,
            "voice": voice,
            "model": "v3turbo",
            "response_format": response_format,
            "speed": speed
        }
        
        start_time = time.time()
        response = requests.post(
            f"{self.base_url}/v1/audio/speech",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        latency = time.time() - start_time
        response.raise_for_status()

        with open(output_file, "wb") as f:
            f.write(response.content)

        return latency

    def test_all_voices(self, text: str, output_dir: str = "test_voices_output") -> None:
        """Lặp qua toàn bộ voice khả dụng và lưu từng file âm thanh tương ứng."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        voices = self.get_available_voices()
        total = len(voices)
        print(f"Tìm thấy {total} giọng đọc. Bắt đầu tổng hợp vào thư mục: '{output_dir}/'\n")

        for index, item in enumerate(voices, start=1):
            v_id = item["id"]
            v_name = item["name"]
            v_region = item.get("region", "Unknown")
            v_gender = item.get("gender", "Unknown")

            file_name = output_path / f"{index:02d}_{v_id}.wav"

            print(f"[{index:02d}/{total:02d}] Voice: {v_name:<15} ({v_id}) | {v_gender} | Miền {v_region} -> ", end="", flush=True)

            try:
                latency = self.generate_speech(
                    text=text,
                    voice=v_id,
                    output_file=str(file_name)
                )
                file_size_kb = file_name.stat().st_size / 1024
                print(f"OK (Latency: {latency:.2f}s, Kích thước: {file_size_kb:.1f} KB)")
            except requests.exceptions.RequestException as error:
                print(f"LỖI: {error}")


if __name__ == "__main__":
    client = TTSClient("http://127.0.0.1:15186")

    # 1. Ping Server
    print("--- 1. Kiểm tra trạng thái máy chủ ---")
    try:
        health_info = client.check_health()
        print(f"Status: {health_info.get('status')} | Device: {health_info.get('device')} | VRAM: {health_info.get('vram_used_mb')} MB\n")
    except requests.exceptions.ConnectionError:
        print("Không thể kết nối đến Server! Hãy chắc chắn server `app.py` đã chạy trên port 7865.")
        exit(1)

    # 2. Test toàn bộ giọng
    print("--- 2. Bắt đầu test tất cả các voice ---")
    sample_text = "Xin chào, đây là câu thoại kiểm tra chất lượng âm thanh của mô hình VieNeu-TTS phiên bản v3 Turbo."
    
    client.test_all_voices(
        text=sample_text,
        output_dir="test_voices_output"
    )