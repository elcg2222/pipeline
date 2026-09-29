# Preview có phụ đề mềm và TTS mẫu

Mở lại `open_preview_tin_tuc.bat` hoặc preview trong app. Launcher mẫu giờ áp dụng
theme như app chính. Màn xem nằm bên trái, bên phải có bốn tab: Phụ đề, Cảnh,
Hồ sơ, TTS mẫu. Tab Hồ sơ/TTS có thanh cuộn cho màn hình thấp.

## Phụ đề

- Sub được vẽ lên canvas theo đồng hồ phát, bên trong vùng hình, không sửa media gốc.
- Bảng hiển thị giờ bắt đầu/kết thúc tới mili giây, tô câu đang chạy. Bấm đúp để seek.
- Có thể tắt lớp sub. Khoảng trống không có câu sẽ không hiển thị chữ cũ.
- Nhập SRT lưu riêng `preview_subtitles.srt`, có backup khi thay file. File này
  được giữ nguyên khi lưu profile và đi cùng ZIP Kaggle.
- Nếu chưa có SRT riêng, dùng SRT dự án đã căn thời gian; với SRT tự sinh một đoạn
  mỗi cảnh, chia thành cụm 10 từ và ước tính theo thời lượng cảnh. Đây **không phải**
  speech alignment. Nhãn trong giao diện cho biết nguồn timing.
- Khi đổi thời lượng, câu ước tính được chia lại. SRT nhập giữ thời gian tuyệt đối;
  người dùng cần căn lại nếu thay giọng hoặc sắp xếp cảnh.
- Remotion preview trong desktop bỏ phần narration đốt sẵn để không chồng hai lớp
  sub. Lớp mềm chỉ hiện trong app; file MP4 cache không chứa lớp này.

## TTS mẫu

Tab TTS mẫu: lấy lời cảnh → chọn giọng/model → Tạo đoạn mẫu → Nghe → Gắn vào cảnh.
Mỗi lần tạo tối đa 1500 ký tự, một yêu cầu Gemini với key đầu tiên đã cấu hình,
không tự retry/đổi key. Có timeout. Nút tạo dùng API/quota; chưa chạy API trực tiếp
trong lượt kiểm thử UI. Model cố định `gemini-3.8-flash-tts` trong Voice Studio.

### Voice Studio trong preview

- Ngôn ngữ: Việt, Anh Mỹ, Anh Anh, Trung, Nhật, Hàn, Pháp, Đức.
- Chỉ dẫn vùng giọng Việt: Bắc/Trung/Nam; sáu kiểu thể hiện, bảy sắc thái,
  giọng nền Aoede/Kore/Puck/Charon/Fenrir và chỉ dẫn riêng tối đa 600 ký tự.
- Lời phải viết sẵn bằng ngôn ngữ muốn đọc. Chọn ngôn ngữ không tự dịch.
  Vùng giọng và persona là chỉ dẫn tạo giọng, cần nghe lại chất lượng thực tế.
- Gọi Gemini Interactions với `speech_metadata.style`, tách chỉ dẫn khỏi nội dung
  đọc. Model luôn là `gemini-3.8-flash-tts`; không fallback sang giọng máy.
- Voice Studio đọc nhiều key từ env/config và mặc định
  `~/Downloads/gemini.txt`; mỗi dòng một key, bỏ dòng trống và dòng bắt đầu `#`.
  Giao diện chỉ hiện số key, không hiện giá trị. Key được xoay vòng và cooldown
  120 giây khi lỗi; key không được ghi vào project, log, preset, profile hoặc ZIP.
- Bộ chỉnh local: tốc độ 0.5–2×, cao độ ±5 bán âm, bass/treble ±12dB,
  vang nhẹ 0–50%, âm lượng 0–150%. Vang dùng short echo, không phải mô phỏng
  phòng bằng convolution. Bộ giới hạn biên độ giảm nguy cơ clipping.
- Tạo mới áp dụng luôn snapshot thông số tại lúc bấm. Đổi thanh chỉnh sau đó cần
  bấm **Áp dụng · không gọi API**. Luôn xử lý lại từ bản gốc, không chồng nhiều lần.
- Có nghe bản gốc/bản đã chỉnh, lịch sử 8 mẫu trong phiên, lưu/nạp thiết lập dự án
  bằng `voice_studio_settings.json`. Lịch sử phiên không tự khôi phục sau khi đóng app.
- Khi gắn audio, `voice_recipe` đi vào scene/profile/ZIP cùng audio thực tế.
  Những thông số chưa áp dụng không được gán nhầm cho audio cũ. Audio nhập ngoài
  được ghi nguồn `imported`, không giả định đã tạo bằng Gemini.

Kiểm chứng bổ sung: `tests/test_voice_studio.py` chạy xử lý WAV thật, kiểm tra
tốc độ/cao độ, mute, bảo toàn bản gốc, contract yêu cầu/phản hồi API bằng fixture,
lịch sử/preset Tk và metadata bàn giao. Chưa dùng quota để kiểm chứng giọng
Gemini thật ở các ngôn ngữ trong lượt nâng cấp này.

App được nối bằng nút mở Vietnamese Multi-Voice Studio và nhập audio tải về:
https://ai-vietnamese-multi-voice-studio.ai.studio/
Đã đọc trang và JavaScript công khai: model khai báo là `gemini-3.8-flash-tts`,
khớp model mặc định của pipeline. App có đường gọi `/api/tts/generate`;
chưa gọi endpoint tạo giọng hoặc nối trực tiếp endpoint đó vào desktop.
Nút tạo mẫu trong desktop hiện gọi Gemini bằng API key người dùng đã cấu hình.
Nguồn Gemini API chính thức: https://ai.google.dev/gemini-api/docs/speech-generation

Nhập WAV/MP3/M4A/OGG/FLAC chuyển bản sao sang WAV 24000Hz mono. Mẫu nằm trong
`.preview_cache/tts`; khi gắn vào cảnh, tạo file riêng trong `audio/`, lưu trường
`reference_audio` trong scene. Có tùy chọn lấy độ dài audio làm độ dài cảnh.
Lưu profile để giữ lựa chọn. Media/audio cũ không bị ghi đè. Audio bàn giao vẫn
`reference_only`, máy Kaggle tạo voiceover cuối và căn lại thời gian.

Kiểm thử bằng `tests/test_preview_captions.py`: biên cue/khoảng trống, seek/tắt bật
overlay Tk, cập nhật timing ước tính, bảo toàn SRT nhập, gắn WAV, lưu và xuất ZIP.
