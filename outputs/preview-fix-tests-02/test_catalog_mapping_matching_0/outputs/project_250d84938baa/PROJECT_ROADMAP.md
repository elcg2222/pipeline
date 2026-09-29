# PROJECT ROADMAP — project_250d84938baa

## Mục đích

Đây là thư mục bàn giao duy nhất của dự án. Agent viết kịch bản/chọn asset phải
đưa file thật vào thư mục này và cập nhật manifest; không chỉ ghi URL hoặc đường
dẫn máy cá nhân. Flow3/Kaggle đọc hồ sơ, không tự đoán ý nghĩa từ tên file.

## Canvas đã chốt

- Tỷ lệ: `16:9`
- Nguồn quyết định: `auto_fallback:no_readable_selected_asset`
- Không tự đổi thành 9:16. Muốn đổi tỷ lệ phải cập nhật brief rồi lưu profile mới.

## Quy tắc cho agent kịch bản và asset

1. Mỗi cảnh có `scene_id`, narration, visual_intent, thời lượng dự kiến và asset_id thật.
2. Chỉ đặt cảnh `ready` sau khi mở/xem asset; khớp từ khóa chưa phải duyệt hình ảnh.
3. Không dùng ảnh placeholder, ảnh gần như một màu, file lỗi hoặc asset không rõ nguồn
   mà không ghi cảnh báo. `asset_quality_warnings` phải được giải quyết trước bàn giao.
4. Phân biệt TTS preview, voice reference và final narration. Preview không phải giọng cuối.
5. SFX/nhạc/layer/font/effect dùng trong bản dựng phải nằm trong thư mục dự án và có cue/role.
6. Timing trước giọng cuối là ước lượng. Kaggle đo voice cuối rồi reflow/alignment.
7. Không đưa API key, token, `.env`, credential, cache, venv hoặc node_modules vào dự án.
8. Nội dung nghiên cứu không tự trở thành bằng chứng bản quyền cho media.

## Trạng thái ban đầu

- Số cảnh: 1
- `preview_profile.json`: hướng dựng local
- `handoff.json`: trạng thái ingest; đọc `missing_assets`, `missing_audio`,
  `asset_quality_warnings` trước khi chạy
- `media/`: ảnh/video thực dùng
- `audio/`: audio mẫu hoặc audio đã đánh dấu vai trò
- `studio.project.json` và `resources/`: được tạo khi dùng cửa sổ Flow3 Studio

## Điều kiện giao Kaggle

Toàn bộ file được tham chiếu phải nằm trong thư mục/ZIP, đường dẫn tương đối, không
có secret; canvas phải rõ ràng; cảnh xanh/placeholder chưa duyệt không được ghi là
hoàn tất. Upload cả thư mục dự án hoặc một ZIP của thư mục, không upload riêng JSON.
