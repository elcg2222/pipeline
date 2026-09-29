# Định hướng pipeline chuẩn bị sản xuất video

## Quy tắc bàn giao hiện hành — 28/09/2026

- Một dự án là một thư mục `project_<id>` chứa roadmap, kịch bản, profile,
  manifest và toàn bộ asset thực dùng. Agent sau đưa cả thư mục/ZIP lên Kaggle.
- Dự án mới mặc định `auto`: tỷ lệ được chốt một lần theo asset đã chọn đầu tiên;
  nếu chưa đọc được asset thì fallback 16:9 và ghi nguồn quyết định trong brief.
  Profile đã chốt 9:16/16:9/1:1 luôn được tôn trọng, preview không tự đổi tỷ lệ.
- Preview local phải cảnh báo ảnh gần như một màu/placeholder. Cùng từ khóa hoặc
  file tồn tại không đủ để đánh dấu asset đã duyệt.
- Mỗi project mới có `PROJECT_ROADMAP.md`. Đây là chỉ dẫn cho agent viết kịch bản,
  chọn asset và đóng gói; không coi các mục lịch sử bên dưới là trạng thái hiện tại.
- `preview_profile.json` là hướng dựng; `studio.project.json` là contract asset/cue;
  TTS mẫu không phải voice cuối. Kaggle reflow sau khi có voice cuối.

## Cập nhật ưu tiên — 27/09/2026

Local là **phòng duyệt hướng dựng**: TTS chỉ làm mẫu; được phép xem thử hiệu ứng bằng Remotion.
Không render sản phẩm cuối ở đây. Sau duyệt, chuyển profile + media/audio mẫu sang Kaggle,
nơi tạo voiceover cuối, căn lại timing, mix và render. Ghi chú duyệt phục vụ hướng dẫn AI/skill sau này,
không đồng nghĩa đã train model hoặc đã có skill renderer.

**Luồng giao diện mới nhất:** gộp vào app desktop hiện có, đúng hai mục chính:
(1) tìm/tải asset theo chủ đề; (2) nhận kịch bản, tách cảnh, ghép asset, preview và xuất ZIP Kaggle.
Remotion/FFmpeg chạy nền local; MP4 nháp và audio phát ngay trong khung app, không bắt mở web Studio.
Quét Groq có xác nhận riêng; gợi ý offline chỉ theo tên/mô tả và cần người dùng duyệt hình ảnh.

Đã bổ sung giao diện preview hai khung; bốn preset chữ Remotion; `preview_profile.json` v2,
revision/backup khi lưu, đánh dấu audio reference_only, duyệt rõ ràng bởi người dùng.
Hướng dẫn và giới hạn hiện tại: `preview_studio/README.md`. Các phần cũ bên dưới là lịch sử;
quy tắc “không hiệu ứng tại local” và “lưu không backup” đã được thay thế bởi mục này.

Ngày đối chiếu: 26/09/2026. Trạng thái: thiết kế đề xuất, chưa phải chức năng đã triển khai.

## Nhật ký chức năng đã làm (từ 26/09/2026)

Lớp `brain/` (AI Brain) + `desktop_app.py` đã có thêm các khối chạy thật trên máy local, tách khỏi phần thiết kế bên dưới:

- **`brain/`** — module AI Brain, chạy độc lập từng khâu: `models` (nạp nhiều key Groq/Gemini), `keypool` (xoay key + cooldown chống Google khóa lưu lượng khi gọi fallback liên tục), `clip` (cắt keyframe bằng ffmpeg), `vision` (Groq `qwen3.8-27b` quét ảnh → JSON caption/OCR/objects, max 3 ảnh/req, free tier OTPM 1000 → `max_completion_tokens≤900`), `scenes` (schema Scene + dựng cảnh từ script.md), `srt` (sinh phụ đề .srt theo thời lượng cảnh), `tts` (CHỈ Gemini TTS, fail thì bỏ qua — KHÔNG fallback edge-tts), `project` (đóng gói `project_<id>/`), `preview` (dựng timeline từ project để xem trước), `produce` (orchestrator end-to-end).
- **CLI `python run.py ai scan|project|status`** — quét asset bằng Groq, đóng gói project, xem cấu hình AI. Key đọc từ `config.yaml` (trường `key_file`) hoặc `Downloads/groq.txt` + `Downloads/gemini.txt` (mỗi dòng 1 key, dòng `#` là chú thích).
- **Timeline Preview kiểu CapCut trong desktop app** — nút "🎞 Xem trước timeline" + bảng "Dự án dựng sẵn" (bấm đúp mở). Cửa sổ preview chiếu asset nối tiếp liên tục, kịch bản/phụ đề chạy bên dưới, thanh tiến trình seek, phát audio qua ffplay — **chưa render thật**. Timeline dạng canvas: **kéo clip để đổi thứ tự, kéo mép phải clip để đổi thời lượng**, toolbar chỉnh trực tiếp (thời lượng/tốc độ/đổi asset/cắt bỏ/lùi-tiến/lưu `scenes.json`).
- **Đọc video** bằng `imageio` + `imageio-ffmpeg` (frame-by-frame), ảnh bằng PIL; thêm vào `requirements.txt` khi đóng gói.
- **Tích hợp Outlier Trend Scoring từ ViralMint (`core/scoring.py`)**:
  Phân loại các video bùng nổ `OUTLIER` ($\ge3\times$), `STRONG` ($\ge5\times$), `BREAKOUT` ($\ge10\times$), `MONSTER` ($\ge20\times$) dựa trên tỉ lệ views / median kênh.
- **Handoff Spec cho Flow3/Flow2 Kaggle (`brain/handoff.py`)**:
  Tự động patch `scenes.json` + `preview_profile.json` + `handoff.json` với các trường chuẩn: `format`, `frame_rate`, `tts_profile`, `voice_resolution`. Sinh audio MP3 thật cho từng cảnh qua Gemini TTS, tạo `media_manifest.json`. Khi Flow3 Kaggle render thật sẽ không báo `missing_audio`.
- **Mọi chỉnh sửa preview ghi đè `scenes.json` (chưa có bản sao lưu tự động)**.
- **Project Sigma Mỹ-Trung demo** (`outputs/project_0d47746d7239/`):
  kiểm tra lại ngày 28/09/2026 thấy 3 cảnh dùng 3 PNG dọc gần như một màu xanh
  (màu trội 99,1–99,3%). Có 3 MP3 và một MP4 final 13,95 MB đã render từ các
  asset xanh này; không tìm thấy 2 video Pexels trong `media/` như mô tả cũ.
  Vì đầu vào hình ảnh là placeholder nên output tồn tại vẫn **không ready cho
  Kaggle**. BAT chỉ mở preview để thay/duyệt lại asset.
- **Kênh Douyin `65763947051` (帅帅小猫)**: Tải 13 video mới nhất (~74 MB) về
  `downloads/douyin_65763947051/` bằng `opencli douyin user-videos` (Chrome login
  Chuminga201 của bạn) + `ffmpeg` kéo thẳng `play_url` từ JSON trả về. Lưu ý:
  opencli `--limit` ở bản 1.8.7 không có flag phân trang, mỗi lần gọi trả 13.
  Cần nâng cấp opencli hoặc viết vòng lặp có `max_cursor` để lấy 29 video bạn yêu cầu.
- **One-click Preview (`open_preview.py` + `open_preview_tin_tuc.bat`)**: Bấm đúp file `.bat` để tự động mở thẳng cửa sổ Preview CapCut cho dự án đã chỉ định mà không cần qua app chính `desktop_app.py`.
- **Nối Provider Stock (`providers/stock_provider.py`)**: Tự động dùng Pexels & Pixabay API kéo video/ảnh dọc (9:16) miễn phí bản quyền thương mại để tự động bù tài nguyên cho cảnh thiếu (`needs_assets`). Key đã lưu tại `config.yaml`.
- **Kho âm thanh local thương mại (`data/audio/`)**: Đã đánh dấu phân loại kho SFX (`whoosh`, `ding`, `pop`, `notification`, `bass_drop`) và kho BGM (`upbeat`, `lofi`, `cinematic`). Hướng dẫn cào Instagram/Facebook tại `data/audio/README_AUDIO_AND_CRAWL.md`.
- **Resource Registry (`data/RESOURCE_REGISTRY.md`)**: Kho tài nguyên sáng tạo video tổng hợp — meme, SFX, storytelling, cộng đồng, phân tầng bản quyền âm thanh 🔴🟡🟢, và **bảng mapping `content_type` → nguồn cào** cho QC/Discover tra cứu tự động.

### 🔧 Hướng nâng cấp QC (CẦN LÀM TIẾP)

QC hiện tại (`stages/qc.py`) chỉ check kỹ thuật: resolution ≥ 720p, duration ≥ 8s, audio stream, pHash dedupe, speech ratio. **Chưa lọc theo chủ đề hay nguồn gốc.**

Các bước nâng cấp dự kiến:
1. **Thêm `content_type` vào `VideoItem` schema** (`core/schema.py`):
   - Giá trị: `product_review`, `meme_compilation`, `storytelling`, `news_commentary`, `sports_highlight`, `film_review`, `funny_animal`, `motivational`
   - Gán tự động bằng keyword matching title/hashtag hoặc AI classification
2. **QC tra bảng `RESOURCE_REGISTRY.md` PHẦN 5** để validate:
   - Video cào từ nguồn đúng với `content_type` của dự án → pass
   - Video từ nguồn không liên quan → giảm điểm hoặc cảnh báo
3. **Thêm `copyright_risk` field** vào `VideoItem`:
   - Tự gán 🔴/🟡/🟢 dựa trên nguồn gốc asset (nhạc/SFX/clip)
   - QC chặn 🔴 tự động, cảnh báo 🟡
4. **Thêm `topic_relevance_score`** vào scoring:
   - So khớp title/hashtag với topic keywords của dự án hiện tại
   - Kết hợp với outlier score để ưu tiên video vừa viral vừa đúng chủ đề

## Định hướng học hỏi từ kiến trúc ViralMint (Dành cho máy Local)

Local **CHỈ** làm nhiệm vụ Viết kịch bản + Tạo bộ khung dự án (Scripting & Skeleton Assembly). Không render nặng, không lồng SFX hay hiệu ứng karaoke tại local. Việc render và lồng hiệu ứng thuộc về agent studio/Colab/Kaggle sau này (sẽ có SKILL.md riêng).

Các điểm học từ ViralMint cho máy Local:
1. **Đánh số thứ tự & Phân đoạn Cảnh chuẩn (Scene Indexing)**:
   - Đánh số thứ tự từng cảnh (`scene_001`, `scene_002`...) kèm mốc thời lượng dự kiến và `visual_intent` để studio edit đọc chuẩn xác 100%.
2. **Quy chuẩn Bộ khung Âm thanh (Audio Skeleton Handoff)**:
   - Học cấu trúc khai báo nhạc nền & điểm ngắt thoại của ViralMint để đóng gói vào file handoff, giúp studio edit biết vị trí cần chèn âm thanh chuyển cảnh/nhạc nền mà không cần tự đoán.
3. **Outlier Trend Scoring (`core/scoring.py`)**:
   - Nhận diện video đột phá từ các kênh nhỏ/trung bình làm đầu vào ý tưởng kịch bản.

---

## 3 Option mở rộng tiếp theo (Cần thảo luận thêm)

- **Option A (Tối ưu Handoff Spec cho máy Edit)**:
  Tập trung chuẩn hóa file `handoff.json` & thư mục `project_<id>/` sao cho gói gọn toàn bộ kịch bản, asset, mốc âm thanh và số thứ tự cảnh. Khi đẩy lên Colab/Kaggle, agent bên studio edit chỉ cần đọc 1 file spec duy nhất là tự render tự động.

- **Option B (Tối ưu Trải nghiệm Dựng sơ bộ tại Local)**:
  Nâng cấp giao diện Preview Timeline trên Tkinter app: cho phép kéo-thả ghép nhanh asset vào kịch bản, cắt/gọt đoạn video sơ bộ, thay đổi vị trí cảnh trực quan mịn màng như CapCut để người dùng duyệt kịch bản ưng ý 100% trước khi xuất gói handoff.

- **Option C (Kết hợp A & B)**:
  Tối ưu cả giao diện làm kịch bản/bộ khung ở local (B) và chuẩn hóa file bàn giao Handoff Spec cho Colab/Kaggle (A).

---

## Phạm vi đã thống nhất

Đầu vào là chủ đề, hashtag hoặc yêu cầu tìm trend. Đầu ra là gói kịch bản và tài nguyên đã gắn với từng cảnh, đủ để dự án dựng video tiếp nhận. Việc cắt ghép, hiệu ứng, phối âm, phụ đề cuối, render MP4 và đăng bài thuộc dự án dựng. Dự án này cần chuẩn bị cả video ngắn và dài, có đường bổ sung tài nguyên bằng AI khi kho tải về không đủ.

Yêu cầu hiện tại là nghiên cứu và đúc kết kiến trúc. Tài liệu này không khẳng định pipeline sản xuất hoàn chỉnh đã được xây hoặc kiểm thử.

## Đánh giá nền tảng hiện có

- `providers/` và `stages/`: tìm video social, tải, chấm điểm, kiểm tra chất lượng; schema `VideoItem` và SQLite riêng.
- `phanmoi/`: ảnh, video stock, RSS; schema `Doc/License`, tìm toàn văn FTS5 và SQLite riêng.
- `media_bridge.py`: nối CLI/desktop với crawler, tải file và lưu manifest.
- Chưa có project brief, hồ sơ nghiên cứu có dẫn nguồn, kịch bản theo cảnh, tìm cảnh theo nội dung hình ảnh, job sinh tài nguyên AI hoặc hợp đồng bàn giao editor.
- Hashtag hiện phụ thuộc adapter (ví dụ Instagram); chưa có chuẩn hashtag xuyên nguồn. Tìm từ khóa chưa chứng minh được một chủ đề đang trend.
- Trường `License.modification_allowed`, `license_url`, `verified_at` có trong schema nhưng chưa được giữ đầy đủ qua bridge/manifest. `commercial_use=True` không đồng nghĩa được tự do chỉnh sửa.
- Bộ tải mới là nền tảng ban đầu: chưa có kiểm tra video stock bằng ffprobe, giới hạn byte tổng, checksum, chống trùng file theo nội dung, khóa job đồng thời và bộ test đủ rộng cho lỗi mạng.

## Luồng đề xuất

1. **Brief**: lưu query, kiểu đầu vào topic/hashtag/trend, ngôn ngữ, đối tượng, góc kể, short/long, thời lượng, tỉ lệ khung, phong cách, ngân sách và chính sách dùng tài nguyên.
2. **Discovery và trend**: mở rộng từ khóa theo ngôn ngữ/nền tảng, giữ provenance của mỗi truy vấn. Với trend, ghi nhiều snapshot theo thời gian: lượt xem, tuổi bài, tốc độ tăng, baseline của kênh và độ phủ nhiều nguồn. Thiếu snapshot thì trả `insufficient_evidence`, không gắn nhãn trend từ tổng view đơn thuần.
3. **Research**: lấy bài viết/trang gốc/transcript để tạo hồ sơ: phát biểu, nguồn URL, đoạn dẫn chứng, ngày xuất bản và thời điểm thu thập. Tách dữ kiện đã kiểm tra, suy luận và nội dung giải trí. Các nguồn bất đồng được ghi lại trước khi viết.
4. **Script**: AI viết dựa trên hồ sơ nghiên cứu. Short gồm hook, diễn tiến và kết; long gồm chương, lập luận và chuyển đoạn. Mỗi cảnh có lời đọc, mục đích hình ảnh, thời lượng dự kiến, từ khóa tìm tài nguyên và `source_ids` hỗ trợ dữ kiện. Đo thời lượng lại bằng voiceover ở bên dựng; số từ chỉ là ước lượng.
5. **Asset matching**: tìm trong kho trước, sau đó tìm bổ sung. Caption hình ảnh, OCR, transcript và keyframe giúp chọn theo nội dung thực tế; FTS5 làm baseline, embeddings bổ sung khi cần. Xếp hạng theo ý nghĩa, độ phân giải, bố cục/crop, thời lượng, độ đa dạng và quyền sử dụng. Lưu phương án thay thế và lý do chọn; không ép chọn cảnh không phù hợp chỉ vì cùng từ khóa.
6. **AI gap filling**: cảnh còn thiếu sinh `generation_request`: prompt, negative prompt nếu hỗ trợ, loại image/video, kích thước, thời lượng, style/character reference, provider, chi phí tối đa và trạng thái. Adapter sinh ảnh/video trả asset về cùng kho, qua QC rồi mới gắn vào cảnh. Job bất đồng bộ cần remote job ID, polling, retry có giới hạn và chống gửi lại gây tính tiền hai lần. Chưa chọn dịch vụ/model cố định khi chưa biết tài khoản và ngân sách thực tế.
7. **Handoff**: đóng gói kịch bản, cảnh, file local, nguồn, giấy phép và khoảng trống còn lại. Chỉ đặt `ready_for_edit` khi mọi cảnh bắt buộc đều có tài nguyên hợp lệ; nếu thiếu, gói ở `needs_assets` và liệt kê rõ cảnh nào.

Tài liệu nghiên cứu là bằng chứng cho lời đọc; ảnh/video là tài nguyên hình ảnh. Đọc một bài để nghiên cứu không có nghĩa toàn bộ bài hoặc media của bài tự động được phép đưa vào sản phẩm.

## Mô hình dữ liệu và bàn giao

Giữ Python + SQLite trong giai đoạn đầu. Bổ sung lớp project dùng chung thay vì lập tức thay cả hai kho cũ. Adapter chuyển `VideoItem` và `Doc` thành Asset tham chiếu kho gốc. CLI và desktop gọi cùng service để tránh hai cách vận hành khác nhau.

Các đối tượng: Project, Brief, TrendSnapshot, Source, Claim, ScriptRevision, Scene, Asset, SceneAsset, GenerationJob, HandoffRevision. ID ổn định, schema có phiên bản; lưu đường dẫn tương đối trong gói xuất để chuyển máy được.

Gói đề xuất:

```text
project_<id>/
  brief.json
  research.md
  sources.jsonl
  script.md
  scenes.json
  assets.jsonl
  generation_requests.jsonl
  attribution.md
  handoff.json
  media/
```

`scenes.json`: scene_id, chapter_id, narration, estimated_duration_sec, visual_intent, source_ids, asset_ids, trim_in/out nếu dùng clip, framing, on_screen_text, alternatives, status. Mốc thời gian là dự kiến trước voiceover, không phải timeline cuối.

`assets.jsonl`: asset_id, relative_path, kind, sha256, source_url, provider, width/height, duration, audio_present, caption/tags, license_id/url, commercial_use, modification_allowed, attribution_required/text, verified_at; tài nguyên AI thêm model, prompt, reference_ids, generation_job_id và generated_at.

`handoff.json`: schema_version, project_id, script_revision, aspect_ratio, target_duration_sec, scene_order, media_root, missing_assets, validation_results, status. Editor trả về receipt chứa project_id, revision và lỗi ingest; thay đổi kịch bản tạo revision mới để không trộn cảnh cũ/mới.

## Chọn công cụ từ tài liệu tham khảo

- **ViralMint**: README xác nhận hướng local-first, scouting, Whisper, viết kịch bản và stock-video generation. Hợp để tham khảo thiết kế hoặc thử tích hợp riêng; chưa có bằng chứng cần thay lõi hiện tại. Số agent/tool và khả năng đăng bài trong bản dán không nên coi là cam kết phiên bản. API bên ngoài vẫn cần được kiểm tra payload; local-first không tự chứng minh xử lý hoàn toàn offline. Nguồn: https://github.com/openclaw-easy/ViralMint
- **shorts-factory**: tham khảo quy trình chọn đề tài và sản xuất Shorts; không coi lịch chạy hay automation trong README là khả năng đã kiểm chứng ở máy này. Nguồn: https://github.com/dikshantbhatia09/shorts-factory
- **faceless-youtube-agents**: tham khảo cách nối nghiên cứu phong cách, kịch bản và sinh tài nguyên. Chỉ học nhịp kể/cấu trúc, cần nội dung và nhận diện riêng. Nguồn: https://github.com/yashaiguy-dev/faceless-youtube-agents
- **Remotion**: ứng viên cho dự án editor; không phải dependency bắt buộc của khâu chuẩn bị. Có điều khoản cấp phép riêng cần đối chiếu mô hình sử dụng, không mặc định mọi quy mô đều miễn phí. Nguồn: https://www.remotion.dev/docs/license
- Synfig, DragonBones, Open Peeps và Humaaans trong bản dán thuộc lựa chọn hoạt hình/nhân vật của editor. Chưa kiểm chứng độc lập trong nghiên cứu này, chưa đưa vào dependency hoặc cam kết giấy phép.

Không cài thêm một hệ thống all-in-one ở bước nghiên cứu này. Ưu tiên hợp đồng trao đổi để sau này dùng editor nào cũng được.

## Thứ tự triển khai và tiêu chí nghiệm thu

### Mốc 1 — Một chủ đề thành gói bàn giao

Chuẩn hóa Brief/Asset/Scene và manifest trước. Dùng nguồn hiện có, research có dẫn chứng, script ngắn/dài, chọn tài nguyên thủ công có hỗ trợ tìm kiếm. Nghiệm thu bằng một chủ đề thật, hai phiên bản short/long, mỗi cảnh gắn file tải hợp lệ; editor đọc gói mà không cần truy cập database nội bộ.

### Mốc 2 — Chọn tài nguyên tự động

Bổ sung caption/OCR/transcript/keyframe, checksum, matching và phương án thay thế. Đánh giá trên bộ cảnh được người dùng gán nhãn phù hợp/không phù hợp; đo tỷ lệ cảnh có tài nguyên được chấp nhận, lỗi file và lựa chọn sai giấy phép. Ngưỡng chất lượng chốt từ dữ liệu mẫu thay vì tự gán con số đẹp.

### Mốc 3 — Hashtag/trend và AI bổ sung

Adapter hashtag rõ năng lực, snapshot trend có thời điểm, generation jobs có ngân sách và provenance. Nghiệm thu bằng một cảnh cố ý thiếu tài nguyên: tạo job, nhận file, QC, gắn lại scene và xuất revision; mất kết nối không sinh job thanh toán trùng.

### Mốc 4 — Chạy lô và tích hợp editor

Queue bền vững, resume, giới hạn request/chi phí/dung lượng và trạng thái UI. Kiểm tra khởi động lại giữa mỗi bước, API hết key, timeout, file hỏng, trùng asset, nguồn biến mất và editor từ chối gói. Không báo hoàn tất khi thiếu cảnh hoặc kiểm chứng nguồn chưa xong.

## Kết luận quyết định

Đối chiếu yêu cầu nghiên cứu:

| Yêu cầu | Kết quả đúc kết | Trạng thái triển khai |
| --- | --- | --- |
| Tìm ảnh, tài liệu, video theo chủ đề | Discovery, Research, kho Asset; tái sử dụng hai khối hiện có | Có nền tảng, chưa thống nhất kho |
| Hashtag hoặc trend | Adapter theo nguồn, snapshot thời gian, bằng chứng tăng trưởng | Cần xây chuẩn chung và đánh giá trend |
| Viết kịch bản dài/ngắn | ScriptRevision, chương/cảnh, dẫn nguồn, thời lượng dự kiến | Chưa triển khai |
| Chọn tài nguyên đã tải phù hợp | SceneAsset, caption/OCR/transcript và phương án thay thế | Chưa triển khai matching |
| Tạo ảnh/video AI khi thiếu | GenerationJob có ngân sách, reference, nhận file và QC | Chưa tích hợp nhà cung cấp |
| Ghép thành sản phẩm hoàn chỉnh qua dự án khác | Handoff có phiên bản, file local, thứ tự cảnh và receipt editor | Đã đề xuất hợp đồng, chưa tích hợp |
| Tìm hiểu và đúc kết phần trên | Đọc bản đính kèm, đối chiếu mã hiện tại và tài liệu nguồn, xác định thứ tự xây | Hoàn tất tài liệu nghiên cứu |

Các tiêu chí nghiệm thu của bốn mốc ở trên là điều kiện cho lần triển khai sau; chưa được tuyên bố đã đạt. Những công cụ hoạt hình dành cho editor được ghi rõ chưa kiểm chứng, không phải lựa chọn đã chốt.

Xây tiếp dự án hiện tại thành công cụ chuẩn bị sản xuất. Ưu tiên đầu ra `ready_for_edit`: nghiên cứu có nguồn + kịch bản theo cảnh + tài nguyên local được chọn + yêu cầu AI cho phần thiếu. Rendering và xuất bản thuộc dự án khác. Bản thiết kế này hoàn tất phần tìm hiểu/đúc kết hiện được yêu cầu; các mốc triển khai ở trên vẫn là công việc tương lai.
