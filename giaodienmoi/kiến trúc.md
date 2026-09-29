# KIẾN TRÚC PIPELINE TỰ ĐỘNG: BRIEF ➔ SCRIPT ➔ VISION ASSET MATCH ➔ HANDOFF

Ngày thiết kế: 26/09/2026.
Tương thích: `D:\pipeline` + `D:\douyinvideo` + Groq API + Gemini API + Hermes + Whisper.

---

## 1. PHÂN CÔNG VAI TRÒ MODEL & TOOL

| Khâu | Model / Công cụ | Vai trò cụ thể | Lý do chọn |
|---|---|---|---|
| **1. Trích Transcript** | `faster-whisper` / `whisperX` (Local/Colab) | Trích xuất toàn bộ lời thoại/âm thanh từ video Douyin/TikTok đã tải | Chạy local GPU miễn phí, không tốn token, chính xác dấu thời gian (timestamps) |
| **2. Nghiên cứu & Viết Kịch bản** | **Hermes Agent** (Trực tiếp) | Đọc tài liệu, tổng hợp brief, viết kịch bản chia theo cảnh (`scenes.json`, `script.md`) | Đồng bộ ngữ cảnh trực tiếp với bạn, linh hoạt điều chỉnh xưng hô/phong cách |
| **3. Vision Scanning & Asset Matching** | **Groq API** (`qwen/qwen3.8-27b`) | Trích xuất 1–3 keyframe từ video/ảnh trong kho, đọc OCR, mô tả góc quay và match vào `scenes.json` | Tốc độ suy luận siêu tốc (LPU Groq), hỗ trợ JSON Mode và Vision 27B |
| **4. Long Context & Backup Brain** | **Gemini Flash** (3.8/3.7/3.6) | Đọc các tài liệu nghiên cứu cực dài hoặc fallback khi Groq chạm limit | Context cực lớn (1M+ token), chi phí token/quota tối ưu |
| **5. Giọng đọc (Voiceover / TTS)** | **Gemini TTS** (Primary) + **Edge-TTS** (Fallback) | Tạo file âm thanh đọc cho từng cảnh dựa trên trường `narration` của scene | Giọng Gemini chất lượng cao, tự nhiên; Edge-TTS cứu cánh khi cần sinh số lượng lớn |

---

## 2. SƠ ĐỒ LUỒNG DỮ LIỆU (END-TO-END FLOW)

```
                       [ CHỦ ĐỀ / TÀI LIỆU / LINK VIDEO ]
                                       │
                                       ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ GIAI ĐOẠN 1: THU THẬP & TRÍCH XUẤT (RAW INGESTION)                        │
 │  • Video Social (Douyin, TikTok, YouTube)  ──► WhisperX ──► transcripts/  │
 │  • Kho Ảnh / Stock (Pexels, Openverse)     ──► media_bridge ──► media/    │
 │  • Tin tức / Bài nghiên cứu (RSS, FTS5)    ──► phanmoi ──► research.md    │
 └─────────────────────────────────────┬─────────────────────────────────────┘
                                       │
                                       ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ GIAI ĐOẠN 2: VIẾT KỊCH BẢN PHÂN CẢNH (HERMES BRAIN)                       │
 │  • Hermes đọc research.md + transcripts                                  │
 │  • Xuất kịch bản `script.md` + file phân cảnh `scenes.json`:              │
 │    - scene_id: 1, 2, 3...                                                │
 │    - narration: Lời đọc tiếng Việt cho cảnh                              │
 │    - visual_intent: Mô tả hình ảnh cần có (ví dụ: "Cận cảnh bàn làm việc")│
 │    - estimated_duration_sec: Thời lượng dự kiến                          │
 └─────────────────────────────────────┬─────────────────────────────────────┘
                                       │
                                       ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ GIAI ĐOẠN 3: VISION SCAN & MATCHING TỰ ĐỘNG (GROQ QWEN 3.8-27B)          │
 │  • Trích xuất keyframes (ffmpeg) từ kho video/ảnh đã tải                 │
 │  • Gửi ảnh qua Groq API (`qwen/qwen3.8-27b`) phân tích:                  │
 │    - Trích xuất: OCR text, vật thể chính, góc quay, độ sắc nét           │
 │  • Đối chiếu với `visual_intent` của từng Scene ──► Gắn `asset_id`       │
 │  • Đánh dấu cảnh thiếu tài nguyên ──► `status: needs_ai_gen`             │
 └─────────────────────────────────────┬─────────────────────────────────────┘
                                       │
                                       ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ GIAI ĐOẠN 4: LỒNG TIẾNG & HOÀN THIỆN GÓI BÀN GIAO (TTS & HANDOFF)         │
 │  • Đọc từng câu `narration` ──► Gemini TTS ──► voiceover_<scene>.mp3     │
 │  • Ghi `manifest.jsonl`, `attribution.md`, `handoff.json`                │
 │  • Xuất trọn vẹn thư mục `project_<id>/` sẵn sàng nạp vào CapCut/Editor  │
 └───────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CẤU TRÚC GÓI BÀN GIAO (`project_<id>/`)

Mỗi dự án sau khi chạy xong sẽ được đóng gói độc lập theo đúng chuẩn `PIPELINE_DIRECTION.md`:

```text
D:\pipeline\outputs\project_20260926_01\
  ├── brief.json              # Đề bài, yêu cầu tỉ lệ khung hình (9:16 / 16:9), tone giọng
  ├── research.md             # Dữ liệu trích xuất từ Whisper / RSS có trích dẫn nguồn
  ├── script.md               # Toàn bộ kịch bản hoàn chỉnh
  ├── scenes.json             # Danh sách phân cảnh chi tiết (gắn asset_id & audio_path)
  ├── assets.jsonl            # Metadata tài nguyên (path, hash, license, OCR/caption)
  ├── handoff.json            # Trạng thái dự án: ready_for_edit
  ├── audio/                  # Các file TTS đã sinh theo từng cảnh
  │     ├── scene_1.mp3
  │     └── scene_2.mp3
  └── media/                  # Video/ảnh local đã chọn khớp với từng cảnh
        ├── clip_01.mp4
        └── image_02.jpg
```
