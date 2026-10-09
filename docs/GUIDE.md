# Hướng Dẫn Sử Dụng VieNeu-TTS GPU Server & Video Novel Pipeline

Tài liệu này hướng dẫn chi tiết cách thiết lập, vận hành hệ thống máy chủ **VieNeu-TTS GPU Server** tích hợp bộ điều khiển **Dynamic VRAM On-Demand Lifecycle Controller**, cùng các công cụ **Client SDK**, **CLI `vieneu`**, **Remotion Video Renderer** và **YouTube Auto-Uploader**.

---

## 📌 1. Tổng Quan Kiến Trúc & Tính Năng chính

- **Zero-VRAM Baseline**: Server khởi chạy ở trạng thái `SLEEP`, chiếm **0 MB VRAM** khi rảnh rỗi và chỉ nạp PyTorch / VieNeu model lên GPU khi nhận lệnh hoặc tác vụ.
- **Supervisor-Worker Process Isolation**: Tách biệt hoàn toàn giữa tiến trình Control Daemon (FastAPI ~25MB RAM) và tiến trình Worker Inference. Khi gọi `unload`, hệ thống gửi `SIGTERM/SIGKILL` giải phóng 100% VRAM GPU về 0 MB tức thì mà không bị rò rỉ CUDA Primary Context.
- **Idle Watchdog Auto-Evict**: Tự động đếm ngược bộ đếm thời gian rảnh rỗi ($N$ giây), tự rút VRAM khi client ngắt kết nối.
- **Python Client SDK & CLI `vieneu`**: Bộ công cụ lập trình Python và dòng lệnh hỗ trợ batch render tiểu thuyết thành video MP4, tự động sắp xếp chương tự nhiên, checkpoint resume và hiển thị tiến trình với `tqdm`.
- **YouTube Data API v3 Auto-Uploader**: Tự động quản lý OAuth2 token, gia hạn tự động, kiểm soát hạn ngạch Quota (10,000 units/ngày) và tải video Resumable chunk 8MB.

---

## 🛠️ 2. Yêu Cầu Hệ Thống & Cài Đặt

### Yêu cầu tối thiểu:
- **Hệ điều hành**: Linux (Ubuntu 20.04/22.04 LTS khuyến nghị)
- **GPU**: NVIDIA GPU hỗ trợ CUDA (RTX 3060/4060 trở lên, VRAM >= 6GB)
- **Phần mềm**: NVIDIA Driver, CUDA Toolkit, FFmpeg, Python 3.10+, `uv` CLI

### Các bước cài đặt:

```bash
# 1. Clone repository
git clone https://github.com/manhtiensle-ops/My_TTS_system.git
cd My_TTS_system

# 2. Chuyển sang nhánh tính năng mới nhất
git switch feature/novel-client-sdk-video

# 3. Tạo môi trường ảo với uv
uv venv .venv
source .venv/bin/activate

# 4. Cài đặt các gói phụ thuộc mà không sửa tay pyproject.toml
uv pip install -r requirements.txt
uv pip install -e . -e sdk
```

---

## ⚙️ 3. Cấu Hình Biến Môi Trường (`.env`)

Tạo file `.env` tại thư mục gốc dự án:

```ini
HOST=0.0.0.0
PORT=7865
LOG_LEVEL=info
DEFAULT_IDLE_TIMEOUT=600

# Cấu hình YouTube Data API v3 (Optional nếu dùng tự động upload)
YOUTUBE_CLIENT_ID=your_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token
```

---

## 🚀 4. Vận Hành GPU Server Backend

### Cách 1: Khởi chạy trực tiếp
```bash
uv run python app.py
```

### Cách 2: Khởi chạy dưới dạng Systemd Service (Khuyến nghị cho Server)
Tạo file `/etc/systemd/system/vieneu-tts.service`:
```ini
[Unit]
Description=VieNeu-TTS Dynamic VRAM On-Demand Server
After=network.target nvidia-persistenced.service

[Service]
Type=simple
User=manhtien
WorkingDirectory=/home/manhtien/workspace/My_TTS_system
ExecStart=/home/manhtien/workspace/My_TTS_system/.venv/bin/python app.py
Restart=always
RestartSec=5
Environment=PATH=/home/manhtien/workspace/My_TTS_system/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin

[Install]
WantedBy=multi-user.target
```

Kích hoạt dịch vụ:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vieneu-tts
sudo systemctl status vieneu-tts
```

---

## 🎮 5. Hướng Dẫn Điều Khiển Dynamic VRAM On-Demand Lifecycle

### 5.1 Sử dụng REST Endpoints
- **Kiểm tra trạng thái GPU**: `GET /v1/lifecycle/status`
- **Nạp Model vào GPU VRAM**: `POST /v1/lifecycle/load`
  ```json
  {
    "model_name": "v3turbo",
    "voice_preload": ["ngoc_huyen", "truc_ly"],
    "idle_timeout_seconds": 600
  }
  ```
- **Giải phóng 100% VRAM về 0 MB**: `POST /v1/lifecycle/unload`
  ```json
  {
    "force": false
  }
  ```
- **Gia hạn Idle Watchdog (Heartbeat)**: `POST /v1/lifecycle/heartbeat`

### 5.2 Sử dụng CLI `vieneu` từ xa
```bash
# Kiểm tra trạng thái GPU trên Server
vieneu --gpu-status

# Nạp model VieNeu lên VRAM GPU
vieneu --load-gpu

# Rút 100% VRAM GPU về 0 MB
vieneu --unload-gpu
```

### 5.3 Sử dụng Python SDK Context Manager (`GPUSession`)
```python
from vieneu_sdk import VieneuClient, GPUSession

client = VieneuClient(base_url="http://100.78.178.23:7865")

# Tự động load VRAM khi vào và tự động unload VRAM về 0 MB khi thoát khối with:
with client.gpu_session(voice_preload=["ngoc_huyen", "truc_ly"]):
    audio_bytes = client.synthesize(
        text="Xin chào, đây là giọng đọc từ VieNeu TTS Server!",
        voice="Ngọc Huyền",
        speed=1.2
    )
```

---

## 🎬 6. Hướng Dẫn Batch Render Video & Đăng YouTube Auto-Uploader

### 6.1 Sử dụng CLI `vieneu`

#### Chuyển đổi folder chương truyện thành Video MP4:
```bash
vieneu --folder ./data/truyen_tien_hiep/chapters \
       --cover ./data/truyen_tien_hiep/cover.jpg \
       --output ./output_mp4 \
       --voice "Ngọc Huyền" \
       --speed 1.2 \
       --start 1 --end 50
```

#### Render Video và Tự Động Upload Lên YouTube:
```bash
vieneu --folder ./data/truyen_tien_hiep/chapters \
       --cover ./data/truyen_tien_hiep/cover.jpg \
       --output ./output_mp4 \
       --voice "Trúc Ly" \
       --upload-youtube \
       --privacy unlisted \
       --playlist "PLxxxxxx"
```

---

## 🧪 7. Chạy Bộ Kiểm Thử (Unit Tests)

Chạy bộ kiểm thử tự động để xác nhận toàn bộ hệ thống hoạt động chính xác:

```bash
uv run pytest -v
```

---

## 📞 8. Liên Hệ & Hỗ Trợ
- **Tác giả / Duyệt dự án**: `manhtiensle-ops`
- **Agent Phân Phối / Animator**: Hermes Animator (`antigravity` / `hermes-CT104`)
