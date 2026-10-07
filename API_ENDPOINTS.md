# API\_ENDPOINTS.md — Đặc tả API Chi tiết

**Base URL:** `http://{GPU_HOST}:{PORT}` (mặc định `http://100.90.61.115:7865`)

---

## 1. `GET /health` — Kiểm tra trạng thái server

Ping server để biết model đã nạp xong vào GPU chưa. **Bắt buộc gọi trước khi gửi job.**

### Request
```
GET /health
```
*(Không có request body)*

### Response — Model sẵn sàng (HTTP 200)
```json
{
  "status": "ok",
  "model_loaded": true,
  "device": "cuda:0",
  "vram_used_mb": 2450.5
}
```

### Response — Đang nạp model (HTTP 503)
```json
{
  "status": "loading",
  "model_loaded": false
}
```

### Ví dụ sử dụng
```bash
curl http://100.90.61.115:7865/health
```

```python
import requests
r = requests.get("http://100.90.61.115:7865/health")
if r.status_code == 200 and r.json()["model_loaded"]:
    print("Server sẵn sàng!")
```

---

## 2. `GET /v1/voices` — Danh sách giọng đọc

Trả về tất cả giọng đọc mà server hỗ trợ.

### Request
```
GET /v1/voices
```

### Response (HTTP 200)
```json
{
  "voices": [
    {"id": "ngoc_huyen", "name": "Ngọc Huyền", "gender": "female", "region": "Bắc"},
    {"id": "truc_ly",    "name": "Trúc Ly",    "gender": "female", "region": "Bắc"},
    {"id": "thai_son",   "name": "Thái Sơn",   "gender": "male",   "region": "Nam"},
    {"id": "mai_anh",    "name": "Mai Anh",     "gender": "female", "region": "Bắc"},
    {"id": "hai_dang",   "name": "Hải Đăng",    "gender": "male",   "region": "Bắc"},
    {"id": "thien_minh", "name": "Thiện Minh",  "gender": "male",   "region": "Bắc"},
    {"id": "adam_bua",   "name": "Adam bựa",    "gender": "male",   "region": "Bắc"},
    {"id": "quang_son",  "name": "Quang Sơn",   "gender": "male",   "region": "Trung"},
    {"id": "ngoc_tran",  "name": "Ngọc Trân",   "gender": "female", "region": "Trung"},
    {"id": "thuy_dung",  "name": "Thùy Dung",   "gender": "female", "region": "Nam"}
  ]
}
```

### Ví dụ
```bash
curl http://100.90.61.115:7865/v1/voices | jq '.voices[].name'
```

---

## 3. `POST /v1/audio/speech` — TTS đoạn ngắn (Video Shorts)

Tổng hợp giọng nói cho đoạn text **ngắn** (voiceover video, thông báo, v.v.). Trả về **binary audio trực tiếp**.

### Request

```
POST /v1/audio/speech
Content-Type: application/json
```

#### Body (JSON)

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `input` | string | ✅ | — | Text tiếng Việt cần đọc (1 – 5,000 ký tự) |
| `voice` | string | ✅ | — | Tên giọng (`"Trúc Ly"`, `"Ngọc Huyền"`, ...) hoặc ID (`"truc_ly"`) |
| `model` | string | ❌ | `"v3turbo"` | Phiên bản model |
| `response_format` | string | ❌ | `"wav"` | `"wav"` hoặc `"mp3"` |
| `speed` | float | ❌ | `1.0` | Tốc độ đọc (0.5 – 2.0) |

#### Ví dụ body — Preset Video Shorts
```json
{
  "input": "Ba xu hướng AI đáng chú ý nhất tuần này. Đầu tiên, OpenAI chính thức ra mắt GPT-5 với khả năng suy luận vượt trội.",
  "voice": "Trúc Ly",
  "speed": 1.1,
  "response_format": "wav"
}
```

### Response — Thành công (HTTP 200)

```
Content-Type: audio/wav          (hoặc audio/mpeg nếu mp3)
Content-Disposition: attachment; filename="speech.wav"
Body: [binary audio bytes]
```

Client nhận binary và lưu thẳng thành file:
```bash
curl -X POST http://100.90.61.115:7865/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Xin chào!", "voice": "Trúc Ly", "speed": 1.1}' \
  --output voiceover.wav
```

```python
import requests

r = requests.post("http://100.90.61.115:7865/v1/audio/speech", json={
    "input": "Xin chào các bạn!",
    "voice": "Trúc Ly",
    "speed": 1.1,
    "response_format": "wav"
})
with open("voiceover.wav", "wb") as f:
    f.write(r.content)
```

### Response — Lỗi (HTTP 400 / 500)

```json
{
  "error": {
    "message": "Voice 'ABC' not found. Available: Trúc Ly, Ngọc Huyền, ...",
    "type": "invalid_request_error",
    "code": 400
  }
}
```

---

## 4. `POST /v1/audio/novel` — TTS truyện dài (MỚI)

Endpoint chuyên xử lý text dài (chapter tiểu thuyết). Server **tự động chia nhỏ** text, TTS từng đoạn, rồi **nối lại** bằng ffmpeg thành 1 file audio hoàn chỉnh.

### Request

```
POST /v1/audio/novel
Content-Type: application/json
```

#### Body (JSON)

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `input` | string | ✅ | — | Toàn bộ nội dung chapter (không giới hạn độ dài) |
| `voice` | string | ❌ | `"Ngọc Huyền"` | Giọng đọc truyện |
| `speed` | float | ❌ | `1.2` | Tốc độ đọc |
| `response_format` | string | ❌ | `"wav"` | `"wav"` hoặc `"mp3"` |
| `chapter_name` | string | ❌ | `""` | Tên chapter (dùng cho log, không ảnh hưởng xử lý) |
| `target_words` | int | ❌ | `100` | Số từ tối thiểu trước khi cắt đoạn tại `\n` |

#### Ví dụ body — Chapter truyện

```json
{
  "input": "Ta, Lý Viễn, chỉ là một sinh viên đại học chỉ muốn sống nhàn giữa thời loạn. Thế nhưng...\nTrong mắt Tào Tháo, ta là một tên khốn ngày nào cũng mong ông ta chết.\nTrong mắt Hạ Hầu Đôn, ta là người cháu hiền tài.\n... (toàn bộ chapter)",
  "voice": "Ngọc Huyền",
  "speed": 1.2,
  "response_format": "mp3",
  "chapter_name": "chap-101",
  "target_words": 100
}
```

### Response — Thành công (HTTP 200)

```
Content-Type: audio/wav          (hoặc audio/mpeg)
Content-Disposition: attachment; filename="chap-101.wav"
X-TTS-Chunks: 12                 (Header tuỳ chọn: số đoạn đã xử lý)
X-TTS-Duration: 342.5            (Header tuỳ chọn: tổng thời lượng audio giây)
Body: [binary audio bytes]
```

#### Ví dụ sử dụng

```bash
# Đọc chapter từ file text
curl -X POST http://100.90.61.115:7865/v1/audio/novel \
  -H "Content-Type: application/json" \
  -d @- --output chap101.mp3 << 'EOF'
{
  "input": "$(cat chap101.txt)",
  "voice": "Ngọc Huyền",
  "speed": 1.2,
  "response_format": "mp3",
  "chapter_name": "chap-101"
}
EOF
```

```python
import requests

chapter_text = open("chap101.txt", "r").read()

r = requests.post("http://100.90.61.115:7865/v1/audio/novel",
    json={
        "input": chapter_text,
        "voice": "Ngọc Huyền",
        "speed": 1.2,
        "response_format": "mp3",
        "chapter_name": "chap-101",
        "target_words": 100
    },
    timeout=600   # Chapter dài có thể mất vài phút
)

with open("chap101.mp3", "wb") as f:
    f.write(r.content)

print(f"Chunks processed: {r.headers.get('X-TTS-Chunks')}")
print(f"Audio duration: {r.headers.get('X-TTS-Duration')}s")
```

### Response — Lỗi

```json
{
  "error": {
    "message": "Inference failed at chunk 7/23: CUDA out of memory",
    "type": "inference_error",
    "code": 500,
    "chunk_failed": 7,
    "total_chunks": 23
  }
}
```

---

## 5. Luồng xử lý nội bộ `/v1/audio/novel`

```
Client ──POST──► FastAPI nhận request
                     │
                     ▼
              Validate (Pydantic NovelRequest)
                     │
                     ▼
              text_splitter.split_chapter(input, target_words=100)
                     │
                     ▼
              Kết quả: ["đoạn 1 (~120 từ)", "đoạn 2 (~105 từ)", ..., "đoạn N"]
                     │
                     ▼
              Tạo thư mục tạm: /tmp/tts_novel_{uuid}/
                     │
                     ▼
              ┌──── Vòng lặp tuần tự ────┐
              │ chunk 0:                  │
              │   engine.synthesize()     │
              │   → part_0000.wav         │
              │ chunk 1:                  │
              │   engine.synthesize()     │
              │   → part_0001.wav         │
              │ ...                       │
              │ chunk N:                  │
              │   engine.synthesize()     │
              │   → part_000N.wav         │
              └───────────────────────────┘
                     │
                     ▼
              audio_concat.concat_wav_files()
              ffmpeg -f concat → final.wav (hoặc .mp3)
                     │
                     ▼
              Đọc binary → Response(content=bytes)
                     │
                     ▼
              Dọn thư mục tạm /tmp/tts_novel_{uuid}/
                     │
                     ▼
              Client nhận file audio hoàn chỉnh
```

---

## 6. Bảng so sánh 2 endpoint TTS

| Tiêu chí | `/v1/audio/speech` | `/v1/audio/novel` |
|---|---|---|
| **Mục đích** | Voiceover video Shorts | Đọc chapter truyện dài |
| **Input** | Text ngắn (50-500 từ) | Text dài (1,000-10,000+ từ) |
| **Voice mặc định** | — (bắt buộc chọn) | Ngọc Huyền |
| **Speed mặc định** | 1.0 | 1.2 |
| **Xử lý** | 1 lần inference | Chia N đoạn → N lần inference → nối |
| **Thời gian** | 1-5 giây | 30 giây – 5 phút |
| **Output** | WAV/MP3 (10-60s audio) | WAV/MP3 (5-30 phút audio) |
| **Timeout khuyến nghị** | 30s | 600s |

---

## 7. HTTP Status Codes

| Code | Ý nghĩa |
|---|---|
| `200` | Thành công — body chứa binary audio |
| `400` | Bad Request — thiếu input, voice không hợp lệ, speed ngoài range |
| `500` | Internal Server Error — GPU inference thất bại, ffmpeg lỗi |
| `503` | Service Unavailable — model chưa nạp xong (gọi `/health` trả `model_loaded: false`) |

---

## 8. `POST /v1/video/novel` — Render Video MP4 Ảnh Tĩnh Cho Chapter Truyện

Tự động chuyển đổi text chapter truyện và file ảnh bìa tĩnh thành video MP4 chuẩn YouTube.

### Request Format
`multipart/form-data`

### Form Fields
| Field | Type | Required | Default | Mô tả |
|---|---|---|---|---|
| `text` | string | **Có** | — | Nội dung văn bản chapter truyện |
| `cover_image` | file | **Có** | — | File ảnh bìa tĩnh (JPG/PNG) |
| `chapter_name` | string | Không | `""` | Tên chapter (ví dụ `"Chương 1"`) |
| `voice` | string | Không | `"Ngọc Huyền"` | Giọng đọc (xem GET /v1/voices) |
| `speed` | float | Không | `1.2` | Tốc độ giọng đọc (0.5 - 2.0) |
| `resolution` | string | Không | `"1920x1080"` | Kích thước video (`"1920x1080"`, `"1280x720"`) |

### Response (HTTP 200)
- **Content-Type**: `video/mp4`
- **Headers**: `Content-Disposition: attachment; filename="{safe_chapter_name}.mp4"`
- **Body**: Binary Video Stream (MP4)
