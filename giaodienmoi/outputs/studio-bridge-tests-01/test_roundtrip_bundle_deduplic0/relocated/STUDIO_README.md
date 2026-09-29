# Studio bridge v1 — opt-in, không thay đổi Colab

Một contract `studio.handoff.v1` cho nhiều producer. Adapter local đã có;
nhánh AI-video trên Kaggle có thể dùng API Python để đăng ký file đã sinh.
Chưa tích hợp một model sinh video hay tự sinh voice cuối.

## Local

Trong tab hướng dựng của preview chọn **Flow3 • Tài nguyên / SFX / gói Studio**.
Profile đã lưu được chuyển sang `studio.project.json` riêng. Thêm file và vai trò,
gắn SFX/nhạc/layer vào scene_start + offset; dùng lại file không nhân bản nội dung.
Xuất Studio ZIP với tên revision mới. ZIP cũ và đường chạy Colab giữ nguyên.
Không tự upload dataset, không copy config/key/venv/node_modules.

Font và voice_reference có thể lưu làm tài nguyên nhưng chưa được bridge tự áp dụng.
Layer ảnh v1 ở giữa, rộng 30%; chưa có UI transform. Xóa cue không xóa file nguồn.
Đóng rồi mở lại cửa sổ để đồng bộ profile mới; nếu đã xóa cảnh có cue, cần bỏ cue
trong studio.project.json trước. Mọi file được đăng ký được đóng gói (kể cả chưa dùng).

## Kaggle

Giải nén ZIP vào thư mục dự án riêng dưới working hoặc dùng cây file dataset.
Đặt thư mục chứa package studio_bridge vào PYTHONPATH (hoặc chạy tại thư mục đó).
Các lệnh sau là Bash/Python CLI, không dùng magic trong file .py:

```bash
python -m studio_bridge.kaggle inspect /kaggle/input/my-project
python -m studio_bridge.kaggle prepare /kaggle/input/my-project --output /kaggle/working/build-001 --draft
```

`--draft` cho phép thiếu giọng cuối và KHÔNG dùng TTS mẫu. Bỏ cờ này thì cảnh
có narration phải có final_audio_id. Bộ chuẩn bị đo audio, nới thời lượng cảnh,
ghép video nền không audio gốc và tạo flow2_package.json + flow3.project.json.
Footage ngắn hơn lời sau reflow gây lỗi: không tự freeze/loop/cắt lời.
Yêu cầu ffmpeg/ffprobe trên PATH; không cài lại Torch/CUDA/system packages.

Sau prepare thành công, dùng bản Flow3 hiện tại đã có môi trường riêng:

```bash
python /kaggle/working/ProductVideo/runtime/flow3_v0_7_relative_timeline_preview_PATCHED.py /kaggle/working/build-001 --project /kaggle/working/build-001/flow3.project.json --working-video /kaggle/working/build-001/working.mp4 --output-dir /kaggle/working/render-001 --renderer ffmpeg --tts-backend mock_silent --render --no-menu
```

Ở lệnh này mock_silent chỉ ngăn Flow3 synth lại; giọng cuối đã được đưa vào
studio_audio theo mốc cảnh. Nếu prepare --draft thiếu giọng, kết quả cũng thiếu giọng.
Tuyệt đối không đổi sang qwen/gemini mà không bỏ audio đã chuẩn bị: sẽ sinh giọng hai lần.
Runtime Flow3 không nằm trong ZIP này; cần dataset/runtime engine riêng đã khóa phiên bản.
Đường dẫn trong ví dụ cần thay theo dataset và vị trí engine thực tế.

## Producer khác / AI-video trực tiếp trên Kaggle

```python
from studio_bridge.project import SCHEMA, register, write
from pathlib import Path

root = Path('/kaggle/working/generated-project')
project = {'schema': SCHEMA, 'project_id': 'ai-video-001', 'producer': 'kaggle_ai_video',
           'aspect_ratio': '9:16', 'fps': 30, 'assets': [], 'scenes': [],
           'cues': [], 'effects_required': []}
asset_id = register(root, project, Path('/kaggle/working/generated.mp4'), 'main_video')
project['scenes'].append({'scene_id': 'scene_001', 'asset_id': asset_id,
                         'duration_s': 3, 'narration': '', 'text_effect': 'static'})
write(root / 'studio.project.json', project)
```

Đầu vào dataset là snapshot chỉ đọc, nhưng producer được tạo file mới trong working
rồi đăng ký vào project ở working. Không cần cập nhật dataset đang gắn cho nhánh này.

## Capability và trạng thái

`inspect` phân biệt đủ file với khả năng renderer. `prepare` chặn effect lạ/chưa hỗ trợ;
không silently downgrade pop/slide của local sang hiệu ứng có tên gần giống.
Hiện bridge cho static/fade/typewriter, layer ảnh, SFX/nhạc và giọng cuối đã cung cấp.
Các cảnh phải dùng cùng subtitle effect; title độc lập khác narration chưa hỗ trợ.
Video layer, word alignment, neon glow, optical blur/interpolation, ducking,
template nâng cao và parity Remotion còn phải triển khai/kiểm thử.
Font mặc định của engine chưa được chứng nhận glyph qua bridge.

package_ready chỉ kiểm tra file/hash/contract, không chứng nhận media decode/giấy phép.
prepared_with_final_audio không phải rendered hay qc_passed. Cần kiểm tra video thật,
nghe audio, căn từ và duyệt bố cục. Không gọi bản này là đủ mọi hiệu ứng trên Kaggle.
