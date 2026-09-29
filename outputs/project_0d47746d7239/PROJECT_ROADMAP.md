# PROJECT ROADMAP — project_0d47746d7239

## Trạng thái đã kiểm tra ngày 28/09/2026

Đây là fixture preview, chưa phải gói sẵn sàng đưa lên Kaggle.

- Canvas do profile chỉ định: `9:16` — preview phải tôn trọng, không tự đổi.
- 3 cảnh, mỗi cảnh đang gắn một PNG 1080×1920.
- Cả ba PNG gần như một màu xanh: màu trội lần lượt khoảng 99,1%, 99,27%, 99,32%.
- Có 3 MP3 trong `audio/`; `flow3_render/` có các clip cảnh và MP4 final đã dựng.
- `media/` không có video nguồn, chỉ có 3 PNG xanh. Output đã render không biến
  placeholder thành asset hợp lệ và không phải bằng chứng project sẵn sàng.
- `source_url` và giấy phép của cả ba asset đang trống.
- Cần thay asset thật hoặc xác nhận có chủ ý trước khi chuyển trạng thái bàn giao.

## Việc agent viết kịch bản/chọn asset phải làm

1. Giữ `scene_id` ổn định; mỗi cảnh phải có narration, visual_intent và file asset thật.
2. Mở/xem trực tiếp asset, không đánh dấu ready chỉ vì tên file khớp từ khóa.
3. Copy mọi ảnh/video/SFX/nhạc/layer/font thực dùng vào thư mục dự án và cập nhật manifest.
4. Ghi rõ vai trò, scene/cue, trim, tốc độ, timing dự kiến và nguồn/license.
5. Không đưa API key, token, credential, cache, venv hoặc node_modules vào đây.
6. TTS local chỉ là preview; voice cuối và word timing được chốt trên Kaggle.
7. Upload cả thư mục này hoặc một ZIP chứa nguyên cây thư mục, không upload riêng JSON.

## Điều kiện sẵn sàng

Chỉ chuyển sang bàn giao khi không còn `missing_assets`, không còn cảnh báo
placeholder chưa giải quyết, tỷ lệ canvas đã được người phụ trách nội dung chốt,
và tất cả đường dẫn đều tương đối, tồn tại bên trong gói.
