# Social Trend Pipeline v2

Bản viết lại của `social_trend_pipeline_v1`, gộp Discovery + Download + QC + cầu nối AutoDub vào **một CLI duy nhất**, không phụ thuộc server nền nào phải bật tay.

---

## 1. Ba điều cần sửa trong kế hoạch cũ

**① OpenCLI không phải là nguồn Discovery cho Douyin.**
Adapter `douyin` của OpenCLI là *Creator Center* — 14 lệnh xoay quanh `publish`, `draft`, `videos`, `stats`, `hashtag`, và nó cần Chrome đã đăng nhập `creator.douyin.com`. Lệnh `douyin search` để tìm video theo từ khoá hiện mới chỉ là một **Pull Request chưa merge** (#1759), và ngay cả khi có thì `plays`, `comments`, `shares` đều trả về `0` vì thẻ kết quả tìm kiếm chỉ hiện lượt like. Pipeline chấm điểm bằng view/engagement sẽ mù hoàn toàn.

**② "Bỏ server cho nhẹ" không đúng với OpenCLI.**
OpenCLI là browser-backed: nó điều khiển Chrome của bạn qua CDP. Bạn không bỏ được server, chỉ đổi từ "2 server Node" sang "1 Chrome phải luôn mở, luôn đăng nhập, không được đụng vào". Trên máy cá nhân dùng chung, đây là nguồn lỗi *khó debug hơn* cổng 3000/8000.

**③ Đúng vai của từng công cụ:**

| Công cụ | Dùng ở đâu | Vì sao |
|---|---|---|
| **f2** (`pip install f2`) | Discovery + Download Douyin/TikTok | Là thư viện Python, `import` thẳng vào process. Không server, không cổng. Đúng thứ bạn muốn. |
| **Douyin_TikTok_Download_API (dtk)** | Backend dự phòng #1 | Self-hosted, `docker compose up`, có identity pool tự vá cookie — ổn định nhất khi chạy dài ngày. |
| **yt-dlp** | Downloader chính + YouTube Shorts | Ổn định nhất cho TikTok/YouTube, chấp nhận được với Douyin. |
| **OpenCLI** | 1688 + **Giai đoạn 5 (đăng bài)** | `opencli 1688 download <offerId>` lấy media trang sản phẩm; adapter Douyin Creator Center dùng để *đăng* video ngược lại. Đây mới là chỗ nó mạnh nhất. |

Vì không backend nào của Douyin sống quá 3 tháng mà không vỡ, code đã thiết kế theo dạng **nhiều backend nối tiếp, fail cái nào tự rơi xuống cái kế tiếp** (`providers.douyin.backends: [dtk, f2, opencli]`).

---

## 2. Kiến trúc v2

```
              ┌──────────────────────────────────────────────┐
  topics ───► │ DISCOVER   douyin│tiktok│1688│youtube        │
              │  ↳ nhiều backend, tự fallback                │
              └───────────────────┬──────────────────────────┘
                                  ▼
              ┌──────────────────────────────────────────────┐
              │ HARD FILTER  view/like/duration/tuổi/keyword  │  ← chặn trước khi tốn băng thông
              │ SCORE        reach + engagement + SAVE RATE   │
              │              + freshness + VELOCITY           │
              │ DIVERSITY    tối đa N video / 1 tác giả       │
              └───────────────────┬──────────────────────────┘
                                  ▼  state = queued
              ┌──────────────────────────────────────────────┐
              │ DOWNLOAD  play_url → yt-dlp → f2 (3 lớp)      │
              │  .part → rename, retry có backoff            │
              └───────────────────┬──────────────────────────┘
                                  ▼  state = downloaded
              ┌──────────────────────────────────────────────┐
              │ QC  ffprobe (res/audio/duration)              │  ← stage mới, quan trọng nhất
              │     Silero VAD (có tiếng người không?)        │
              │     pHash 5 khung (trùng nội dung?)           │
              └───────────────────┬──────────────────────────┘
                                  ▼  state = qc_passed
              ┌──────────────────────────────────────────────┐
              │ BRIDGE  rclone → Drive/autodub/inbox/<batch>  │
              │         + jobs.jsonl (có style, target_lang)  │
              └───────────────────┬──────────────────────────┘
                                  ▼
                    AutoDub trên Kaggle/Colab (Flow 1→2→3)
                                  ▼
              │ COLLECT  rclone ← Drive/autodub/outbox        │
                                  ▼  state = dubbed → published
```

### Những thứ v1 thiếu mà v2 bổ sung

1. **State machine thay cho cờ `downloaded: true`.** 11 trạng thái + `attempts` + `last_error`. Mọi lệnh chạy lại được bao nhiêu lần cũng không tải trùng, không bỏ sót job lỗi dở.
2. **Velocity.** View tăng bao nhiêu **mỗi giờ** giữa 2 lần crawl (bảng `metrics_history`). Đây mới là "đang trend"; công thức cũ chỉ phân biệt được "đã nổi" với "nổi lâu rồi".
3. **Save rate.** Trên Douyin lượt *lưu* (`collect_count`) là tín hiệu ý định mua mạnh nhất — người ta lưu để mua sau. Like chỉ là giải trí. Trọng số 0.20.
4. **Cổng QC.** AutoDub ăn GPU quota Kaggle. Mỗi video rác lọt qua là mất 5–10 phút GPU. Lọc ở local gần như miễn phí: thiếu audio stream, dưới 540p, quá ngắn, **không có tiếng người** (chỉ nhạc nền → Flow 2 không có gì để dịch), hoặc **trùng nội dung**.
5. **Chống trùng theo nội dung, không chỉ theo URL.** pHash 5 khung hình + majority vote. Một clip Douyin bị đăng lại lên TikTok có URL khác hoàn toàn nhưng pHash gần như y hệt — v1 sẽ lồng tiếng và đăng 2 lần.
6. **Diversity cap.** Không để 1 kênh chiếm hết Top 20.
7. **Cầu nối AutoDub.** V1 dừng ở `download_queue.jsonl` rồi... để đó. PC ở Windows, AutoDub ở cloud — v2 dùng Google Drive làm hàng đợi bất đồng bộ qua `rclone`, notebook chỉ cần đọc đúng 1 file `jobs.jsonl`.
8. **`python run.py doctor`.** Kiểm tra sạch môi trường trước khi chạy thay vì để nó chết giữa chừng.

---

## 3. Cài đặt (Windows 10)

```powershell
cd D:\pipelinevideo\social_trend_pipeline_v2
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# ffmpeg - bắt buộc cho QC
winget install Gyan.FFmpeg

# rclone - cho cầu nối AutoDub
winget install Rclone.Rclone
rclone config          # tạo remote tên "gdrive" trỏ tới Google Drive

python run.py doctor   # phải xanh hết trước khi đi tiếp
```

### Backend dtk (khuyến nghị cho chạy dài ngày)

```powershell
git clone https://github.com/hex2rgb/Douyin_TikTok_Download_API
cd Douyin_TikTok_Download_API
docker compose up -d
```
Rồi đặt `providers.douyin.dtk_base_url: http://127.0.0.1:8080` trong `config.yaml`.

### Cookie Douyin (cho backend f2)

Mở `douyin.com` trong Chrome đã đăng nhập → F12 → Network → chọn request bất kỳ tới `douyin.com` → copy nguyên header `Cookie`. Dán vào biến môi trường:

```powershell
setx DOUYIN_COOKIE "ttwid=...; odin_tt=...; sessionid=..."
```

Cookie hết hạn khoảng 2–4 tuần. Khi `doctor` báo backend f2 lỗi, lấy lại cookie là xong.

---

## 4. Vận hành

```powershell
python run.py doctor                   # kiểm tra môi trường
python run.py discover                 # quét toàn bộ topics trong config
python run.py discover -t "颈椎按摩仪"  # quét 1 từ khoá
python run.py download --limit 10
python run.py qc
python run.py export                   # đẩy sang AutoDub qua Drive
python run.py collect                  # thu video đã lồng tiếng về
python run.py all                      # chạy liền mạch 4 bước đầu
python run.py status                   # xem pipeline đang tắc ở đâu
python run.py recheck                  # xét lại video rejected theo cấu hình hiện tại
python run.py retry                    # mở lại các video đã hết lượt thử tải
python run.py add --url "https://www.instagram.com/reel/..."  # thêm URL công khai
python run.py media search "meme" --type image --commercial-only --save
```

`add` dùng yt-dlp, nên có thể nhận URL công khai từ Facebook, Instagram và
nhiều website khác mà yt-dlp hỗ trợ. Nội dung riêng tư, DRM, hoặc bị website
chặn vẫn không thể tải chỉ bằng công cụ này; dùng cookie của tài khoản có quyền
truy cập trong `download.cookies_from_browser` khi phù hợp.

`media search --save` tải song song qua file `.part`, retry khi mạng chập chờn,
xác minh ảnh và ghi `manifest.jsonl` cạnh file để giữ nguồn cùng thông tin giấy
phép. Nội dung bị đánh dấu cấm thương mại sẽ không được lưu, trừ khi chủ động
thêm `--allow-restricted`.

### Discovery Reddit + Instagram

Reddit được quét bằng OpenCLI (`reddit search`) nên cần Chrome đăng nhập Reddit
và Browser Bridge đang kết nối. Instagram dùng Instaloader quét hashtag đã khai
báo trong `providers.instagram.topic_hashtags`; cần session local, không đặt mật
khẩu vào `config.yaml`. Sau khi cấu hình session, chạy `python run.py doctor` để
kiểm tra, rồi dùng `python run.py discover`. Cả hai nguồn chỉ tạo metadata trong
SQLite; stage `download` vẫn dùng yt-dlp thống nhất như các nguồn khác.

### Dashboard theo dõi và vận hành

```powershell
cd D:\pipeline
python dashboard.py
```

Trình duyệt sẽ mở tại `http://127.0.0.1:8765`. Dashboard hiển thị rõ video
đến từ **Douyin, TikTok, YouTube hay 1688**, trạng thái từng video, số lần tải
lại, lỗi gần nhất và lịch sử chạy. Có thể bấm chạy từng bước từ giao diện.
Dashboard chỉ lắng nghe trên máy của bạn (`127.0.0.1`), không công khai ra mạng.

### Ứng dụng desktop (không dùng trình duyệt)

Nhấp đúp `start_desktop_app.bat`, hoặc chạy:

```powershell
cd D:\pipeline
python desktop_app.py
```

Đây là giao diện cửa sổ cục bộ, không mở HTTP server. Có thể dán tối đa 20 URL
video công khai từ Facebook, Instagram, Reddit, Discord attachment/CDN, TikTok,
YouTube và các trang khác mà yt-dlp nhận diện được. Dùng `build_desktop_app.bat`
khi muốn tạo `PipelineDesktop.exe`; sau khi build, chép file `.exe` về thư mục
pipeline để ứng dụng dùng cùng database và cấu hình hiện có.

### Chạy tự động (Task Scheduler)

Tạo `daily.bat`:
```bat
cd /d D:\pipelinevideo\social_trend_pipeline_v2
call .venv\Scripts\activate
python run.py all --limit 15
```
Lịch gợi ý: `discover` 3 lần/ngày (8h, 14h, 20h) — chạy nhiều lần mới có **2 điểm đo để tính velocity**. `download` + `qc` chạy ban đêm.

---

## 5. Hai mẹo tăng chất lượng đầu vào nhiều nhất

**Dùng từ khoá tiếng Trung cho Douyin và 1688.** `颈椎按摩仪` ra gấp ~10 lần kết quả so với "máy massage cổ", và đó là video review gốc của nhà sản xuất — đúng thứ bạn cần. File config đã để sẵn vài ví dụ.

**Bật `qc.check_speech`.** Rất nhiều video Douyin đẹp nhưng chỉ có nhạc nền + chữ chạy trên màn hình. AutoDub Flow 2 không có gì để dịch, Flow 3 lồng tiếng vào khoảng trống → ra video vô nghĩa. Cần cài `torch` (~2GB) nhưng lọc rất sạch. Với các video kiểu này, hướng đúng là **tự viết kịch bản tiếng Việt rồi TTS đè lên**, không phải dịch.

### Về khâu TTS trong AutoDub

Nếu Flow 3 đang dùng giọng đọc chung, đổi sang model có voice cloning tiếng Việt sẽ nâng chất lượng rõ rệt — cùng một "gương mặt giọng nói" trên mọi video giúp kênh có nhận diện:

- **VieNeu-TTS** (0.3B / 0.5B, có bản GGUF) — clone giọng từ 3–5 giây mẫu, chạy được CPU, có sẵn giọng Bắc/Nam nam & nữ.
- **viet-tts** (dangvansam) — API tương thích chuẩn OpenAI TTS nên ghép vào pipeline rất nhanh, ~30 giọng dựng sẵn, chạy Docker.
- **F5-TTS-Vietnamese** — chất lượng cao nhất nếu bạn chịu fine-tune, nhưng nặng và cần GPU.

---

## 6. Giai đoạn 5 — Xuất bản

Chỗ này OpenCLI mới thực sự đáng dùng: adapter Douyin Creator Center có pipeline `publish` 8 pha (upload TOS multipart có resume → cover → chờ transcode → kiểm duyệt nội dung → tạo bài). Với Facebook/TikTok Shop thì dùng Graph API và TikTok Content Posting API chính thức, ổn định hơn nhiều so với tự động hoá trình duyệt.

Stage này **chưa viết code** — tôi để lại sau khi 4 stage đầu chạy ổn định, vì mỗi kênh có luồng xác thực riêng và nên làm từng kênh một.

---

## 7. Một lưu ý thực tế

Tải video người khác, xoá watermark rồi đăng lại là điểm rủi ro của mô hình này — cả về bản quyền lẫn thuật toán nền tảng (Facebook/TikTok đều phát hiện nội dung đăng lại và bóp reach). Cách làm giảm rủi ro mà vẫn giữ được năng suất:

- Ưu tiên nguồn **1688/Taobao**: video mô tả sản phẩm do chính nhà cung cấp làm ra để người bán sử dụng — đây là nguồn "sạch" nhất về mặt sử dụng lại.
- Với video Douyin của creator, coi nó là **tư liệu thô**, không phải sản phẩm cuối: cắt lại, đổi nhịp dựng, thêm intro/outro riêng, overlay logo, viết lại kịch bản thay vì dịch nguyên văn. Pipeline đã trả về `score` và metadata đủ để bạn chọn ra ít video hơn nhưng làm kỹ hơn — thực tế cho ra kết quả tốt hơn là đăng ồ ạt.

---

## Cấu trúc file

```
run.py                      CLI duy nhất
config.yaml                 toàn bộ cấu hình
core/schema.py              VideoItem + chuẩn hoá URL/số liệu (1.2万 → 12000)
core/store.py               SQLite, state machine, velocity, pHash lookup
core/scoring.py             hard filter + công thức điểm + diversity
core/util.py                subprocess an toàn trên Windows, retry backoff
providers/douyin_tiktok.py  4 backend: dtk / f2 / opencli / apify
providers/marketplace.py    1688 (OpenCLI) + YouTube Shorts (yt-dlp)
stages/discover.py
stages/download.py          3 lớp fallback
stages/qc.py                ffprobe + VAD + pHash
stages/bridge_autodub.py    export/collect qua rclone
```
