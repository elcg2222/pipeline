# Local Direction Preview

Local dùng để duyệt hình ảnh, nhịp, chữ và TTS mẫu. Kaggle tạo voiceover, căn lại timing,
mix âm thanh và render cuối. Ghi chú review là dữ liệu hướng dẫn cho AI, **không tự train model**.

## Dùng trong desktop

Ứng dụng desktop hiện có đúng **hai mục chính**, không cần mở web trong luồng thông thường:

1. **Tìm asset theo chủ đề**: tìm/tải ảnh, video, tin tức; nút **Dùng kho này → mục 2** nối kho tải với khâu dựng.
2. **Kịch bản → Preview → Kaggle**:
   - Nhập/dán `.md` hoặc `.txt`; `## Tên cảnh` hoặc mỗi đoạn cách dòng trống là một cảnh.
   - Đọc kho, lọc theo tên/mô tả, chọn cảnh + asset rồi gán; hoặc gợi ý các cảnh còn trống.
   - Gợi ý dùng từ khóa trong tên/mô tả đã có, **không phải tự hiểu hình ảnh**. Không tự ghi đè lựa chọn tay.
   - Nút quét Groq là tùy chọn có xác nhận gửi asset ra API; dùng quota đã cấu hình. Xong đọc lại kho.
   - **Tạo hồ sơ → xem trong app**: chỉ copy các asset đã gắn/các phương án thay thế, không copy cả kho.
   - Chỉnh chữ `fade / slide / pop / typewriter`, thời lượng, tốc độ và ghi chú.
   - **Dựng preview hiệu ứng ngay trong app** gọi Remotion nền, xuất MP4 50% resolution / 2 worker,
     rồi phát bằng khung native trong chính mục 2. Không mở Studio/browser. Sửa cảnh làm bản render cũ hết hiệu lực.
   - **Lưu profile nháp** cập nhật scenes, subtitles, handoff và preview_profile; có backup trong revisions/.
   - **Duyệt hướng dựng**, sau đó **Xuất gói ZIP cho Kaggle**. ZIP chỉ gồm hồ sơ và media/audio tham chiếu,
     không gồm config, key, cache hoặc revisions. Xuất bản chưa duyệt vẫn giữ trạng thái draft.

Trang **Mở dự án đã có** nằm trong mục 2; preview không mở thành cửa sổ riêng.
Sửa kịch bản trong trang chuẩn bị rồi tạo hồ sơ sẽ tạo dự án mới, không ghi đè dự án đang duyệt.
Gói chuyển sang Kaggle có `preview_profile.json` dùng đường dẫn tương đối,
   audio_role=reference_only, final_voiceover_required=true. Profile có thể đã duyệt hướng
   nhưng còn thiếu asset; handoff chỉ approved_for_edit khi có đủ media.

## Cài / chạy lại (Windows, Linux, Colab)

Node.js >= 16, Python cho bridge. Trong thư mục này chạy `npm ci`.
Desktop: từ gốc repo chạy `python desktop_app.py` hoặc launcher đã có.
`npm run dev` chỉ dành cho phát triển template nâng cao, không cần cho luồng desktop.
Từ gốc repo: `python -m brain.remotion_bridge outputs/project_x`.
Chỉ chuẩn bị dữ liệu: thêm `--stage-only`. Script Python không có notebook magic.
Remotion cần tải Chrome Headless Shell ở lần render đầu; Linux cần thư viện hệ thống theo tài liệu Remotion.

- `npm run check`: kiểm tra TypeScript.
- `npm run still`: render ảnh thử ở out/preview.png.
- `npm run preview`: MP4 xem trước độ phân giải 50%, tối đa 2 worker (không phải bản cuối).

Studio dùng một profile hoạt động tại một thời điểm; mở dự án khác sẽ thay profile đang xem.
Chỉ media/audio được tham chiếu được chép vào public/projects; không chép key, config hoặc research.
Launcher `studio.cjs` ép các TCP listener của tiến trình về 127.0.0.1; không publish thư mục public.
Không chạy trực tiếp `npx remotion studio` cho hồ sơ riêng tư: bản Remotion này mặc định bind mọi interface.
Studio phát triển có thể tiếp tục chạy độc lập. Ctrl+C trong terminal dùng để mở Studio.
App không dừng tiến trình Studio do phiên khác mở. Renderer nền của app có nút hủy riêng.

TTS Gemini tùy chọn: cấu hình `ai.preview_tts: true` mới gọi trong production; mặc định tắt để tránh tốn quota.
SDK: `python -m pip install google-genai`. TTS PCM được đóng WAV mono 24 kHz (hoặc sample rate do API trả).
Màn Tkinter phát audio ngay trong app qua pygame-ce; FFmpeg giải mã sang OGG 44.1 kHz stereo để seek.
Cài: `python -m pip install pygame-ce==2.5.8 imageio-ffmpeg`.
FFmpeg ưu tiên PATH, nếu thiếu dùng binary đi kèm imageio-ffmpeg. Không cần ffplay.
Máy Colab/headless vẫn dùng được phần xử lý/đóng gói/render; GUI và thiết bị loa chỉ dùng trên desktop.
Không có fallback TTS khác. Audio cũ gắn đuôi MP3 nhưng chứa PCM phải tạo lại, không tự sửa byte bằng đổi tên.

## Phạm vi hiện tại

4 preset chữ, image/video, trim_in, playback_rate, phụ đề theo cảnh và audio mẫu.
Chưa có editor keyframe tùy ý, karaoke căn từng từ, transition phức tạp hay adapter Kaggle thực thi.
Các hiệu ứng nâng cao có thể viết thêm trong src/index.tsx; máy render phải dùng cùng template/version
hoặc tự ánh xạ các trường profile. Không khẳng định hiệu ứng đã chạy được trên máy Kaggle chưa kiểm tra.
License: https://www.remotion.dev/docs/license — kiểm tra điều kiện trước khi dùng thương mại theo tổ chức.
