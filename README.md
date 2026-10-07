# My\_TTS\_System — Hệ thống Tổng hợp Giọng nói Tiếng Việt

Hệ thống TTS (Text-to-Speech) tiếng Việt chất lượng cao dựa trên **VieNeu-TTS v3 Turbo**, chạy trên GPU NVIDIA CUDA, phục vụ **2 mục tiêu sản xuất nội dung chính**:

| Mục tiêu | Mô tả | Voice mặc định | Speed |
|---|---|---|---|
| 🎬 **Video Shorts** | Voiceover cho TikTok / YouTube Shorts / Reels (9:16) | Trúc Ly | 1.1 |
| 📖 **Truyện Audio** | Đọc tiểu thuyết mạng, chia chapter thành audio dài | Ngọc Huyền | 1.2 |
| 🎬 **Truyện Video MP4** | Chuyển đổi folder truyện + ảnh bìa thành video MP4 YouTube | Ngọc Huyền | 1.2 |

---

## Cài đặt & Sử dụng Client SDK / CLI (Mới)

Sử dụng `vieneu-sdk` ở phía Client để tự động scan folder truyện, chọn số lượng chapter, render video MP4 và tự động upload lên YouTube.

### 1. Khởi tạo Môi trường & Cài đặt

#### Cách 1: Sử dụng `uv` (Khuyên dùng — Cực nhanh)
```bash
# 1. Khởi tạo virtualenv bằng uv
uv venv .venv

# 2. Cài đặt SDK và dependencies phía Client bằng uv pip
uv pip install -e ./sdk

# 3. Kích hoạt môi trường
source .venv/bin/activate
```

#### Cách 2: Sử dụng Python `venv` / `pip` truyền thống
```bash
# 1. Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# 2. Cài đặt SDK
pip install -e ./sdk
```

---

### 2. Thực thi Lệnh CLI `vieneu`

```bash
# Chạy lệnh CLI chuyển đổi folder truyện thành MP4:
vieneu --folder ./data/truyen_tien_hiep/chapters \
       --cover ./data/truyen_tien_hiep/cover.jpg \
       --output ./output_mp4 \
       --voice "Ngọc Huyền" \
       --speed 1.2 \
       --start 1 --end 50

# Hoặc vừa render vừa tự động đăng lên YouTube:
vieneu --folder ./data/truyen_tien_hiep/chapters \
       --cover ./data/truyen_tien_hiep/cover.jpg \
       --output ./output_mp4 \
       --upload-youtube \
       --privacy unlisted \
       --playlist "PLxxxxxx"

# Mẹo: Chạy trực tiếp bằng `uv run` mà không cần activate .venv:
uv run vieneu --folder ./data/truyen_tien_hiep/chapters --cover ./data/truyen_tien_hiep/cover.jpg --output ./output_mp4
```

---

## Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │ Hermes Agent │    │ Script thủ công / Ứng dụng khác  │   │
│  │ (Cronjob     │    │ (curl, Python requests, v.v.)    │   │
│  │  ban đêm)    │    │                                  │   │
│  └──────┬───────┘    └──────────────┬───────────────────┘   │
│         │                           │                       │
│         ▼     HTTP REST API         ▼                       │
│  ════════════════════════════════════════════════════════    │
│         │          GPU SERVER (100.90.61.115:7865)           │
│  ┌──────▼───────────────────────────────────────────────┐   │
│  │                   FastAPI (app.py)                    │   │
│  │  ┌────────────┐ ┌──────────────┐ ┌────────────────┐  │   │
│  │  │ GET /health│ │GET /v1/voices│ │POST /v1/audio/ │  │   │
│  │  │            │ │              │ │     speech      │  │   │
│  │  └────────────┘ └──────────────┘ └──────┬─────────┘  │   │
│  │                                         │            │   │
│  │  ┌──────────────────────────────────────▼─────────┐  │   │
│  │  │          POST /v1/audio/novel                  │  │   │
│  │  │  (Endpoint mới — xử lý truyện dài)             │  │   │
│  │  │  1. Nhận full text chapter                     │  │   │
│  │  │  2. Chia nhỏ đoạn ~100-200 từ (thuật toán \n)  │  │   │
│  │  │  3. TTS từng đoạn nhỏ → WAV tạm               │  │   │
│  │  │  4. ffmpeg nối WAV → 1 file audio hoàn chỉnh   │  │   │
│  │  │  5. Trả về binary audio bytes                  │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                         │                            │   │
│  │  ┌──────────────────────▼────────────────────────┐   │   │
│  │  │            engine.py (VieNeuEngine)            │   │   │
│  │  │  • load_model(): Nạp VieNeu v3 Turbo → VRAM   │   │   │
│  │  │  • synthesize(): Text → audio numpy array      │   │   │
│  │  │  • unload_model(): Giải phóng VRAM             │   │   │
│  │  │  • threading.Lock bảo vệ CUDA Graph            │   │   │
│  │  └──────────────────────┬────────────────────────┘   │   │
│  │                         │                            │   │
│  │  ┌──────────────────────▼────────────────────────┐   │   │
│  │  │         NVIDIA GPU (RTX 4060/4070)             │   │   │
│  │  │         CUDA 12.x │ PyTorch 2.8               │   │   │
│  │  │         VieNeu-TTS v3 Turbo (VRAM ~2-3GB)     │   │   │
│  │  └───────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Cấu trúc thư mục dự án (OOP Modular Layout)

```
My_TTS_system/
├── src/                               # Toàn bộ mã nguồn cốt lõi (Module hóa)
│   ├── api/                           # Tầng Giao tiếp HTTP (FastAPI Routers)
│   │   ├── routes/
│   │   │   ├── health.py              # GET /health
│   │   │   ├── voices.py              # GET /v1/voices
│   │   │   ├── speech.py              # POST /v1/audio/speech
│   │   │   └── novel.py               # POST /v1/audio/novel
│   │   ├── dependencies.py            # Singleton Engine & Service dependencies
│   │   └── router.py                  # Tổng hợp các route
│   ├── engines/                       # Tầng Engine trừu tượng (OOP BaseTTSEngine)
│   │   ├── base.py                    # BaseTTSEngine (ABC interface)
│   │   └── vieneu.py                  # VieNeuEngine (Implementation GPU inference)
│   ├── processors/                    # Tầng xử lý chuyên biệt (OOP Processors)
│   │   ├── text_splitter.py           # NovelTextSplitter (Chia đoạn ~100-200 từ ngắt tại \n)
│   │   └── audio_concat.py            # AudioConcatenator (FFmpeg demuxer ghép audio)
│   ├── services/                      # Tầng Nghiệp vụ (Business Pipeline)
│   │   └── novel_service.py           # NovelPipelineService (Quản lý chu trình đọc truyện)
│   ├── schemas/                       # Pydantic Schemas / DTOs
│   │   ├── health.py                  # HealthResponse
│   │   ├── voice.py                   # VoiceItem, VoicesResponse
│   │   ├── speech.py                  # SpeechRequest
│   │   └── novel.py                   # NovelRequest
│   └── config.py                      # Cấu hình tập trung (HOST, PORT, TMP_DIR, Presets)
├── scripts/                           # Các script kiểm thử & benchmark độc lập
│   ├── benchmark_direct.py            # Chạy benchmark inference trực tiếp với VieNeu
│   ├── test_client.py                 # Client test các API endpoint
│   └── test_all_voices.py             # Client test kiểm tra 25 giọng đọc
├── tests/                             # Unit tests tự động cho logic xử lý
│   ├── test_text_splitter.py          # Unit test thuật toán ngắt dòng thông minh
│   └── test_audio_concat.py           # Unit test nối audio bằng FFmpeg
├── samples/                           # Mẫu audio đầu ra của hệ thống
├── app.py                             # Entrypoint chính khởi chạy FastAPI Server
├── requirements.txt                   # Danh sách thư viện cài đặt chuẩn
├── Dockerfile                         # Docker image CUDA runtime
├── docker-compose.yml                 # Docker Compose với GPU reservation
├── README.md                          # Tài liệu hướng dẫn
├── ARCHITECTURE.md                    # Thiết kế kiến trúc chi tiết
├── API_ENDPOINTS.md                   # Đặc tả API chi tiết
└── pyproject.toml                     # Metadata dự án
```

---

## Cài đặt thư viện: `requirements.txt`

Không dùng lockfile phức tạp (`uv.lock`), chỉ cần dùng file `requirements.txt` chuẩn:

```bash
# Cài đặt bằng uv pip (nhanh và đơn giản):
uv pip install -r requirements.txt

# Hoặc nếu dùng pip thông thường:
pip install -r requirements.txt
```

---

## Hướng dẫn nhanh

### Chạy server

```bash
# Kích hoạt virtualenv (nếu có) rồi chạy:
python app.py

# Hoặc qua uv:
uv run python app.py
```

### Chạy server (Docker — dùng cho production)

```bash
docker compose up -d
# Server khởi động tại http://0.0.0.0:7865
# Chờ 30-60s để nạp model vào GPU
```

### Test health

```bash
curl http://localhost:7865/health
```

### Tạo voiceover video Shorts (Trúc Ly, speed 1.1)

```bash
curl -X POST http://localhost:7865/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Xin chào các bạn!", "voice": "Trúc Ly", "speed": 1.1}' \
  --output voiceover.wav
```

### Tạo audio chapter truyện (Ngọc Huyền, speed 1.2)

```bash
curl -X POST http://localhost:7865/v1/audio/novel \
  -H "Content-Type: application/json" \
  -d '{"input": "Toàn bộ nội dung chapter...", "voice": "Ngọc Huyền", "speed": 1.2, "chapter_name": "chap-101"}' \
  --output chap101.wav
```

---

## Hai luồng xử lý chính

### Luồng 1: Video Shorts / TikTok
```
Text kịch bản (ngắn, ~50-500 từ)
    │
    ▼
POST /v1/audio/speech
    │
    ▼
Engine.synthesize() → 1 lần inference
    │
    ▼
Trả về WAV/MP3 binary
```

### Luồng 2: Truyện tiểu thuyết mạng
```
Text chapter dài (1,000 - 10,000+ từ)
    │
    ▼
POST /v1/audio/novel
    │
    ▼
text_splitter.split_chapter()
    │ Chia thành N đoạn ~100-200 từ
    │ Cắt tại ký tự '\n' sau khi đếm đủ ~100 từ
    ▼
Vòng lặp: Engine.synthesize(đoạn_i) → WAV tạm
    │  đoạn 1 → /tmp/chap101_001.wav
    │  đoạn 2 → /tmp/chap101_002.wav
    │  ...
    │  đoạn N → /tmp/chap101_00N.wav
    ▼
audio_concat.concat_wav(danh sách WAV)
    │ ffmpeg -i "concat:..." → 1 file WAV hoàn chỉnh
    ▼
Dọn file tạm → Trả về WAV binary
```

---

## Phần cứng & Vận hành

- **GPU:** NVIDIA RTX 4060 (8GB) hoặc RTX 4070 (12GB)
- **Cổng:** `7865` (cấu hình qua biến môi trường `PORT`)
- **Lịch chạy:** Chỉ hoạt động **02:00 – 05:00 sáng** để tiết kiệm điện
- **Pipeline tự động:** Hermes Agent cronjob quét hàng đợi job và gọi API

---

## Tài liệu bổ sung

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Thiết kế kiến trúc chi tiết từng module
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) — Đặc tả request/response cho tất cả endpoint
