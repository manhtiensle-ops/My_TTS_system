import time
from typing import Dict, Any
import requests

class TTSClient:
    """Client tương tác với máy chủ TTS chuẩn OpenAI."""

    def __init__(self, base_url: str = "http://127.0.0.1:7865"):
        self.base_url = base_url.rstrip("/")

    def check_health(self) -> Dict[str, Any]:
        """Kiểm tra độ sẵn sàng của máy chủ và trạng thái VRAM."""
        response = requests.get(f"{self.base_url}/health")
        print(f"Health Status: {response.status_code}")
        return response.json()

    def get_available_voices(self) -> Dict[str, Any]:
        """Lấy danh sách các giọng đọc được nạp."""
        response = requests.get(f"{self.base_url}/v1/voices")
        response.raise_for_status()
        return response.json()

    def generate_speech(
        self,
        text: str,
        voice: str = "Ngọc Huyền",
        speed: float = 1.0,
        response_format: str = "wav",
        output_file: str = "result.wav"
    ) -> None:
        """Gửi văn bản cần đọc và ghi binary stream ra file cục bộ."""
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
            headers={"Content-Type": "application/json"}
        )
        latency = time.time() - start_time
        
        if response.status_code != 200:
            print(f"Lỗi ({response.status_code}): {response.text}")
            return
            
        with open(output_file, "wb") as f:
            f.write(response.content)
            
        print(f"Thành công! File lưu tại: {output_file} (Thời gian xử lý: {latency:.2f}s, Kích thước: {len(response.content)} bytes)")

if __name__ == "__main__":
    client = TTSClient("http://127.0.0.1:7865")
    
    print("--- 1. Kiểm tra trạng thái GPU ---")
    try:
        health_info = client.check_health()
        print(health_info)
    except requests.exceptions.ConnectionError:
        print("Server chưa chạy hoặc sai địa chỉ IP/Port!")
        exit(1)

    print("\n--- 2. Lấy danh sách giọng đọc ---")
    voices_info = client.get_available_voices()
    for v in voices_info.get("voices", []):
        print(f"- {v['name']} ({v['id']}): {v['gender']} | {v['region']}")

    print("\n--- 3. Gửi văn bản tổng hợp giọng nói ---")
    sample_text = "Xin chào các bạn, đây là luồng thử nghiệm máy chủ âm thanh VieNeu-TTS v3 Turbo chạy trên card đồ họa rời."
    client.generate_speech(
        text=sample_text,
        voice="ngoc_huyen",
        speed=1.2,
        response_format="wav",
        output_file="test_api_output.wav"
    )