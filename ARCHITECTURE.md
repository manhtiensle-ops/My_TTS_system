# ARCHITECTURE.md — Thiết kế Kiến trúc Chi tiết

## 1. Tổng quan lớp (Layer Overview)

```
┌─────────────────────────────────────────────────────────┐
│                    TRANSPORT LAYER                       │
│              FastAPI + Uvicorn (1 worker)                │
│    Nhận HTTP request, validate, trả binary audio        │
├─────────────────────────────────────────────────────────┤
│                   PROCESSING LAYER                       │
│         text_splitter.py  +  audio_concat.py            │
│    Chia text dài → đoạn nhỏ, nối WAV → file hoàn chỉnh │
├─────────────────────────────────────────────────────────┤
│                    ENGINE LAYER                          │
│               engine.py (VieNeuEngine)                   │
│     Quản lý vòng đời model, inference trên CUDA         │
├─────────────────────────────────────────────────────────┤
│                   HARDWARE LAYER                         │
│          NVIDIA GPU + CUDA + PyTorch + VieNeu            │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Module chi tiết (OOP Architecture)

### 2.1 Cấu trúc OOP 4 Tầng (Clean Architecture)

```
┌────────────────────────────────────────────────────────┐
│               TẦNG 1: HTTP TRANSPORT (API)              │
│   FastAPI Routers: /health, /voices, /speech, /novel  │
│   Request/Response Schemas: Pydantic Validation        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│              TẦNG 2: BUSINESS SERVICES                 │
│   NovelPipelineService: Điều phối chia text, gọi       │
│   engine tuần tự, nối audio và dọn dẹp file tạm        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│               TẦNG 3: DOMAIN PROCESSORS                │
│   - NovelTextSplitter: Ngắt đoạn theo threshold & '\n' │
│   - AudioConcatenator: Bọc FFmpeg demuxer ghép audio   │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│              TẦNG 4: CORE TTS ENGINES                  │
│   - BaseTTSEngine (Abstract Base Class Interface)      │
│   - VieNeuEngine (Thực thi model GPU VRAM)             │
│   - [Tương lai]: F5TTSEngine, KokoroEngine, etc.       │
└────────────────────────────────────────────────────────┘
```

### 2.2 `src/engines/` — Tầng Core Engine (Kế thừa BaseTTSEngine)

- `BaseTTSEngine` (ABC): Định nghĩa interface chuẩn (`load_model`, `unload_model`, `synthesize`, `resolve_voice`, `get_status`, `list_voices`).
- `VieNeuEngine`: Cài đặt cụ thể cho mô hình VieNeu-TTS v3 Turbo, bảo vệ CUDA Graph bằng `threading.Lock`. Tương lai có thể dễ dàng cắm thêm các engine khác (Kokoro, F5-TTS, Edge-TTS) mà không làm đổi cấu trúc API.

**Nguyên tắc quan trọng:**
- `synthesize()` chỉ nên nhận đoạn text **ngắn** (~100-500 từ) để đảm bảo ổn định VRAM
- Text quá dài (>1000 từ) có thể gây tràn VRAM hoặc chất lượng giảm → cần chia nhỏ trước

---

### 2.2 `text_splitter.py` — Module chia nhỏ văn bản (MỚI)

```python
def split_chapter(text: str, target_words: int = 100) -> list[str]:
    """
    Chia text dài thành các đoạn nhỏ ~100-200 từ.

    Thuật toán:
    1. Tách text thành danh sách các dòng theo '\n'
    2. Duyệt từng dòng, cộng dồn số từ vào bộ đếm
    3. Khi bộ đếm >= target_words (mặc định 100):
       → Cắt tại vị trí '\n' này
       → Reset bộ đếm, bắt đầu đoạn mới
    4. Đoạn cuối cùng gom phần còn lại (có thể < 100 từ)

    Ví dụ:
        Input:  chapter dài 2500 từ, có 40 dòng
        Output: list gồm ~20-25 đoạn, mỗi đoạn 100-200 từ

    Tại sao cắt theo '\n':
    - Đơn giản, dự đoán được, không phá vỡ ngữ cảnh câu
    - Truyện mạng thường có '\n' sau mỗi 1-3 câu sẵn rồi
    - Giọng đọc TTS sẽ có khoảng nghỉ tự nhiên giữa các đoạn
    """
```

**Ví dụ minh họa thuật toán:**

```
Dòng 1 (15 từ)     ─┐
Dòng 2 (22 từ)      ├── Đoạn 1 (tổng 65 từ, chưa đủ 100 → tiếp tục)
Dòng 3 (28 từ)      │
Dòng 4 (35 từ)     ─┘── Đoạn 1 (tổng 100 từ ≥ 100 → CẮT!)
                         ► Xuất đoạn 1

Dòng 5 (40 từ)     ─┐
Dòng 6 (18 từ)      ├── Đoạn 2 (tổng 58 từ, chưa đủ → tiếp tục)
Dòng 7 (55 từ)     ─┘── Đoạn 2 (tổng 113 từ ≥ 100 → CẮT!)
                         ► Xuất đoạn 2
...
```

---

### 2.3 `audio_concat.py` — Module nối audio bằng ffmpeg (MỚI)

```python
def concat_wav_files(wav_paths: list[str], output_path: str) -> str:
    """
    Nối danh sách file WAV thành 1 file WAV duy nhất bằng ffmpeg.

    Quy trình:
    1. Tạo file danh sách concat (filelist.txt):
       file '/tmp/chap101_001.wav'
       file '/tmp/chap101_002.wav'
       ...
    2. Gọi ffmpeg:
       ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.wav
       (dùng -c copy vì tất cả đều cùng format WAV 48kHz mono,
        không cần re-encode → nhanh gần như tức thì)
    3. Dọn file tạm (filelist.txt + các WAV đoạn nhỏ)
    4. Trả về đường dẫn file output

    Tại sao dùng ffmpeg mà không nối numpy array:
    - Xử lý ngoài Python → không chiếm RAM Python
    - Tốc độ rất nhanh (copy codec, không re-encode)
    - Đáng tin cậy, xử lý header WAV chính xác
    - Dễ chuyển sang MP3 output nếu cần
    """


def concat_and_convert_mp3(wav_paths: list[str], output_path: str, bitrate: str = "192k") -> str:
    """
    Nối WAV + chuyển đổi sang MP3 trong 1 bước ffmpeg.
    ffmpeg -f concat -safe 0 -i filelist.txt -b:a 192k output.mp3
    """
```

---

### 2.4 `app.py` — FastAPI Server (Mở rộng)

Giữ nguyên cấu trúc hiện tại, **thêm 1 endpoint mới** cho truyện dài:

```python
# ── ENDPOINT CŨ (giữ nguyên) ───────────────────────────
GET  /health              # Kiểm tra model sẵn sàng
GET  /v1/voices           # Danh sách giọng đọc
POST /v1/audio/speech     # TTS đoạn ngắn (video Shorts)

# ── ENDPOINT MỚI ───────────────────────────────────────
POST /v1/audio/novel      # TTS truyện dài (chia nhỏ + nối audio)
```

**Luồng xử lý endpoint `/v1/audio/novel`:**

```
Client gửi POST /v1/audio/novel
    │
    ▼
Validate request (Pydantic: NovelRequest)
    │
    ▼
text_splitter.split_chapter(input_text, target_words=100)
    │ → Trả về list[str]: ["đoạn 1", "đoạn 2", ..., "đoạn N"]
    ▼
Tạo thư mục tạm: /tmp/tts_novel_{uuid}/
    │
    ▼
for i, chunk in enumerate(chunks):    ← Vòng lặp tuần tự
    │   audio = engine.synthesize(chunk, voice, speed)
    │   engine.save(audio, f"/tmp/tts_novel_{uuid}/part_{i:04d}.wav")
    │
    ▼
audio_concat.concat_wav_files(
    wav_paths = [part_0000.wav, part_0001.wav, ...],
    output_path = f"/tmp/tts_novel_{uuid}/final.wav"
)
    │
    ▼
Đọc binary final.wav → StreamingResponse trả về client
    │
    ▼
Dọn dẹp thư mục tạm /tmp/tts_novel_{uuid}/
```

---

### 2.5 `schemas.py` — Pydantic Models (Mở rộng)

```python
# ── Giữ nguyên ─────────────────────────────────
class SpeechRequest          # POST /v1/audio/speech
class HealthResponse         # GET /health
class VoiceItem, VoicesResponse  # GET /v1/voices

# ── Thêm mới ───────────────────────────────────
class NovelRequest(BaseModel):
    input: str               # Toàn bộ text chapter (bắt buộc)
    voice: str = "Ngọc Huyền"  # Mặc định voice truyện
    speed: float = 1.2       # Mặc định tốc độ truyện
    response_format: str = "wav"  # wav hoặc mp3
    chapter_name: str = ""   # Tên chapter (tuỳ chọn, dùng đặt tên file log)
    target_words: int = 100  # Số từ tối thiểu trước khi cắt đoạn

class NovelProgress(BaseModel):
    chapter_name: str
    total_chunks: int
    processed_chunks: int
    status: str              # "processing" | "concatenating" | "done"
```

---

## 3. Luồng dữ liệu hoàn chỉnh

### 3.1 Luồng Video Shorts (đơn giản, đã hoạt động)

```
┌──────────┐    POST /v1/audio/speech       ┌──────────────┐
│  Hermes  │ ──────────────────────────────► │   FastAPI     │
│  Agent   │    {"input": "Kịch bản ngắn",  │              │
│          │     "voice": "Trúc Ly",        │  engine       │
│          │     "speed": 1.1}              │  .synthesize()│
│          │ ◄────────────────────────────── │              │
│          │    binary WAV (10-60 giây)      └──────────────┘
└──────────┘
     │
     ▼
  Remotion render → video MP4
```

### 3.2 Luồng Truyện tiểu thuyết (mới, cần xây dựng)

```
┌──────────┐    POST /v1/audio/novel        ┌──────────────────────────┐
│  Client  │ ──────────────────────────────► │       FastAPI            │
│  (curl / │    {"input": "Chapter dài...", │                          │
│  Python) │     "voice": "Ngọc Huyền",    │  1. split_chapter()      │
│          │     "speed": 1.2,             │     → 20 đoạn nhỏ        │
│          │     "chapter_name":"chap101"} │                          │
│          │                                │  2. for đoạn in đoạn_s: │
│          │                                │       synthesize(đoạn)   │
│          │                                │       → part_0001.wav    │
│          │                                │       → part_0002.wav    │
│          │                                │       → ...              │
│          │                                │                          │
│          │                                │  3. ffmpeg concat        │
│          │                                │     → chap101.wav        │
│          │ ◄────────────────────────────── │                          │
│          │    binary WAV (~5-15 phút audio)│  4. trả binary + dọn tmp│
└──────────┘                                └──────────────────────────┘
```

---

## 4. Quy ước Voice Preset

Hệ thống định nghĩa sẵn 2 bộ preset mặc định:

| Preset ID | Mục đích | Voice | Speed | Endpoint |
|---|---|---|---|---|
| `video_shorts` | Voiceover TikTok, YouTube Shorts, Reels | Trúc Ly | 1.1 | `/v1/audio/speech` |
| `novel_reader` | Đọc truyện tiểu thuyết mạng | Ngọc Huyền | 1.2 | `/v1/audio/novel` |

---

## 5. Xử lý lỗi & Edge Cases

| Tình huống | Xử lý |
|---|---|
| Text chapter rỗng hoặc quá ngắn (<5 từ) | HTTP 400: `"Input quá ngắn"` |
| Voice không tồn tại | HTTP 400: `"Voice 'XYZ' not found"` |
| GPU VRAM tràn khi inference 1 đoạn | Đoạn text quá dài → `split_chapter` với `target_words` nhỏ hơn; engine tự xử lý OOM bằng try/except |
| ffmpeg không được cài | HTTP 500: `"ffmpeg not found"` (kiểm tra lúc startup) |
| Inference 1 đoạn thất bại giữa chừng | Dọn file tạm đã tạo, trả HTTP 500 kèm số thứ tự đoạn lỗi |
| Client timeout (chapter quá dài, >10 phút xử lý) | Đặt timeout hợp lý phía client (~300-600s cho 1 chapter) |

---

## 6. File tạm & Dọn dẹp

```
/tmp/tts_novel_{uuid}/
├── part_0000.wav      ← đoạn 1
├── part_0001.wav      ← đoạn 2
├── ...
├── part_00NN.wav      ← đoạn N
├── filelist.txt       ← danh sách concat cho ffmpeg
└── final.wav          ← kết quả nối hoàn chỉnh

→ Toàn bộ thư mục bị xóa sau khi trả response cho client
→ Nếu server crash giữa chừng: /tmp tự dọn khi reboot hoặc cron cleanup
```

---

## 7. Giới hạn & Lưu ý

- **1 request tại 1 thời điểm:** GPU chỉ xử lý 1 inference tại 1 thời điểm (threading.Lock). Các request khác xếp hàng chờ.
- **VRAM:** Model chiếm ~2-3GB. Phần còn lại dùng cho inference. RTX 4060 (8GB) hoặc 4070 (12GB) đều đủ.
- **Dung lượng audio:** WAV 48kHz mono ≈ 5.5 MB/phút. Chapter 10 phút ≈ 55MB WAV (nên dùng MP3 cho truyện dài).

---

## 8. Kiến trúc Client SDK & Video Renderer (`feature/novel-client-sdk-video`)

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER (sdk/vieneu_sdk)            │
│  ┌────────────────────┐   ┌──────────────────────────────┐  │
│  │  NaturalSorter     │   │  NovelBatchProcessor         │  │
│  │  (chap_1->chap_10) │   │  - range & limit filter      │  │
│  └─────────┬──────────┘   │  - checkpoint & resume state │  │
│            │              └──────────────┬───────────────┘  │
│            └──────────────┬──────────────┘                  │
│                           ▼                                 │
│                    VieneuClient (HTTP)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │ POST /v1/video/novel (Multipart)
┌───────────────────────────▼─────────────────────────────────┐
│                    BACKEND GPU SERVER LAYER                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  NovelVideoService                                    │  │
│  │  1. NovelPipelineService -> Sinh MP3 giọng Ngọc Huyền │  │
│  │  2. StillImageVideoRenderer -> FFmpeg still-image MP4 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```
- **Thời gian xử lý:** RTF ~0.15-0.25 (nhanh hơn real-time 4-6x). Chapter 10 phút audio ≈ 2-3 phút xử lý GPU.

---

## 9. Kiến trúc YouTube Data API v3 Auto-Uploader (`vieneu_sdk/youtube/`)

### Cấu trúc Module Client:
- `YouTubeConfig`: Đọc `CLIENT_ID`, `CLIENT_SECRET`, `REFRESH_TOKEN` từ `.env`.
- `YouTubeAuthManager`: Xác thực OAuth2, tự động refresh token, lưu cache tại `~/.vieneu/youtube_token.json`.
- `QuotaTracker`: Ghi nhận hạn ngạch 10,000 units/ngày, cảnh báo dừng an toàn khi hết quota.
- `NovelMetadataBuilder`: Chuẩn hóa Tiêu đề (<=100 ký tự), Mô tả SEO, Tags, Playlist, Thumbnail.
- `YouTubeUploader`: Resumable Upload 8MB chunks kèm Exponential Backoff khi gián đoạn mạng.
