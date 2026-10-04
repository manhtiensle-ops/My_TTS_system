# My\_TTS\_System — Hệ thống Tổng hợp Giọng nói Tiếng Việt

Hệ thống TTS (Text-to-Speech) tiếng Việt chất lượng cao dựa trên **VieNeu-TTS v3 Turbo**, chạy trên GPU NVIDIA CUDA, phục vụ **2 mục tiêu sản xuất nội dung chính**:

| Mục tiêu | Mô tả | Voice mặc định | Speed |
|---|---|---|---|
| 🎬 **Video Shorts** | Voiceover cho TikTok / YouTube Shorts / Reels (9:16) | Trúc Ly | 1.1 |
| 📖 **Truyện Audio** | Đọc tiểu thuyết mạng, chia chapter thành audio dài | Ngọc Huyền | 1.2 |

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

## Cấu trúc thư mục dự án

```
My_TTS_system/
├── app.py                  # FastAPI server — tất cả endpoints
├── engine.py               # VieNeuEngine — nạp model, inference GPU
├── schemas.py              # Pydantic models (request/response validation)
├── text_splitter.py        # [MỚI] Thuật toán chia nhỏ text truyện dài
├── audio_concat.py         # [MỚI] Nối các đoạn WAV bằng ffmpeg
├── Dockerfile              # Docker image CUDA runtime
├── docker-compose.yml      # Docker Compose với GPU reservation
├── README.md               # Tài liệu này
├── ARCHITECTURE.md         # Thiết kế kiến trúc chi tiết
├── API_ENDPOINTS.md        # Đặc tả API chi tiết
├── test_voices_output/     # Mẫu audio test các giọng đọc
└── pyproject.toml          # Python project metadata
```

---

## Quản lý Python: `uv`

Dự án sử dụng **[uv](https://docs.astral.sh/uv/)** để quản lý Python, dependencies và virtualenv. Không dùng `pip` / `venv` trực tiếp.

```bash
# Cài uv (nếu chưa có)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài dependencies (tự tạo .venv + cài packages)
uv sync

# Chạy server trực tiếp qua uv
uv run python app.py

# Thêm dependency mới
uv add fastapi uvicorn pydub

# Chạy script test
uv run python main.py
```

---

## Hướng dẫn nhanh

### Chạy server (Native với uv — khuyên dùng khi dev)

```bash
uv sync                    # Cài dependencies
uv run python app.py       # Server chạy tại http://0.0.0.0:7865
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
