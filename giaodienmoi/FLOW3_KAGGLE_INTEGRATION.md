# Pipeline → Flow3 Studio → Kaggle

Ngày khảo sát: 2026-09-28. Thiết kế gốc bên dưới; đã triển khai bridge v1 độc lập, chưa nghiệm thu Kaggle.

## Cập nhật triển khai v1

Module `studio_bridge/` và cửa sổ `ui_studio_handoff.py` đã có: asset/cue contract,
copy tài nguyên theo hash, Studio ZIP riêng, preflight, prepare montage/Flow2/Flow3,
và gọi engine được chỉ định bằng CLI. Luồng Colab và exporter cũ không bị thay thế.
Nhánh AI video có API đăng ký file trực tiếp trong working; chưa nối model sinh video.
Chi tiết chạy và giới hạn: `studio_bridge/README.md`.

Smoke thực trên Windows đã tạo clip qua đúng Flow3 PATCHED: 2,5 giây, 1080x1080,
audio stereo 48000 Hz và chữ Xin chào. Audio fixture là sine, không phải TTS.
Đây không phải bằng chứng cho toàn bộ hiệu ứng hay cho môi trường Kaggle.
Bản v1 vẫn thiếu nhiều yêu cầu đích ở các mục sau, đặc biệt hiệu ứng nâng cao,
alignment, UI transform và tự sinh giọng cuối. Không coi toàn bộ thiết kế đã hoàn tất.

## 1. Kết luận

Giữ một app local: tìm asset → viết kịch bản → dựng/duyệt preview → xuất dự án. Flow3 là máy dựng/Studio trên Kaggle, không phải một pipeline sáng tác độc lập phải nhập tay lại.

TTS local mặc định là giọng mẫu để duyệt hướng dựng. Không tự coi nó là giọng cuối hoặc mẫu clone giọng. Giữ ba khái niệm riêng: preview narration, voice-cloning reference, final narration.

Mỗi bản xuất là một snapshot tự đủ tài nguyên đã chọn, với manifest vai trò và timeline có cấu trúc. Không chỉ đặt tên thư mục SFX/layer rồi yêu cầu AI đoán cách sử dụng.

## 2. Bằng chứng từ mã hiện tại

Nguồn pipeline: `brain/profile.py`, `brain/assembly.py`, `brain/project.py`.
Nguồn Studio: thư mục `runtime` của `thumuctool`, đặc biệt:

- `flow3_v0_7_relative_timeline_preview_PATCHED.py`: load_flow2_package_v2, process_local, _build_tts_track, render_video.
- `flow3_schema.py`: load_project, project_to_legacy_layers.
- `flow3_studio_styles.py`: audio_settings và cấu hình subtitle_style.
- `flow3_renderers.py`, `flow3_remotion/render.mjs`.

Entrypoint được người dùng chỉ định có SHA256:
`EC8EF99508AB6C527A8D8B69C570DBA0ABBAE47BD5047A6D6AA144ED2C911FB3`.
Đây là định danh bản khảo sát, không phải chứng nhận chất lượng.

| Thành phần | Hiện trạng | Hệ quả tích hợp |
|---|---|---|
| Pipeline profile | preview_profile.json, schema_version 2, cảnh/media/audio/voice_recipe | Không phải flow3.project.v2 dù cùng số 2 |
| Pipeline export | Whitelist hồ sơ và media/audio được cảnh tham chiếu | Chưa gom tùy ý SFX, layer, font, dependency của preset |
| Flow3 process_local | Vẫn đọc flow2_package.json và một working video khi có --project | Không nhận trực tiếp danh sách cảnh của pipeline |
| Flow3 project v2 | Track có tỷ lệ thời gian, transform, style | Cần compiler; schema khai báo được không đồng nghĩa renderer dựng được |
| Nhạc/SFX FFmpeg | metadata.subtitle_style.studio_audio: path/start_s/gain_db/loop | Đã có mã mix; không cần viết lại từ đầu |
| Đường dẫn audio | audio_settings không tự rebase path theo file project như track.source | Adapter phải resolve mọi dependency, không chỉ track |
| Timing lời | TTS được đặt vào start_ms; track cuối cắt theo duration đã có | Không tự reflow theo độ dài speech thật; có nguy cơ chồng/cắt lời |
| Lỗi tài nguyên/TTS | Một số nhánh log rồi bỏ qua | Cần gate thiếu dữ liệu và QC chặt trước khi báo thành công |
| Remotion | Nhánh process_local từ chối nhiều studio effect/audio settings | Ưu tiên FFmpeg cho cầu nối đầu tiên; không hứa giống hệt preview local |

Tài liệu roadmap có nhắc hai bản PATCHED; lần khảo sát này chỉ tìm được một entrypoint Flow3 PATCHED trong cây file. Test contract vẫn tham chiếu tên runtime cũ. Cần cập nhật test/discovery trước nghiệm thu; không lấy kết quả test của bản cũ làm bằng chứng cho bản này.

## 3. Cấu trúc gói dự án đề xuất

```text
project_<id>/
  project.json                 # ID, revision, schema, canvas, engine requirement
  assets.manifest.json         # danh mục tài nguyên + checksum + vai trò
  edit.timeline.json           # cảnh, cue, layer, audio, liên kết hiệu ứng
  preview_profile.json         # ý đồ đã duyệt ở local
  brief.json
  script.md
  voice_recipe.json           # thiết lập giọng, KHÔNG chứa key
  media/video/
  media/images/
  audio/preview/              # TTS mẫu, không mặc định đưa vào final
  audio/reference/            # chỉ dùng clone khi được chỉ định rõ
  audio/final/                # nếu đã cung cấp giọng cuối
  audio/music/
  audio/sfx/
  layers/images/
  layers/video/
  layers/masks/
  fonts/                      # file thực và giấy phép
  effects/                    # preset đã khóa phiên bản + dependency
  subtitles/                  # text/timing; ghi rõ estimated hay aligned
  provenance/                 # nguồn, attribution, license
  reports/preflight.json
```

Tên/schema mới trong tài liệu này là đề xuất, chưa phải đầu vào runtime hỗ trợ. Có thể giữ cấu trúc thư mục cũ trong giai đoạn chuyển tiếp; manifest mới là nguồn ánh xạ chính. Chỉ sao chép dependency thực dùng, không sao chép toàn kho và không đổi file nguồn người dùng.

### Asset: file là gì?

Mỗi asset có `asset_id`, `kind`, `roles`, `path` tương đối POSIX, `sha256`, `size_bytes`, thông số đo thực (duration, kích thước, fps, sample rate, channels, alpha nếu có), mô tả/tag, nguồn/license và `required`.

Roles gồm main_video, broll, still, preview_narration, voice_reference, final_narration, music, sfx, overlay_image, overlay_video, mask, font, effect_config, caption_timing. Kind chỉ là video/image/audio/font/json; không suy vai trò từ phần mở rộng. Một file có thể có nhiều cách dùng.

### Cue: file được dùng thế nào?

Mỗi lần sử dụng có `cue_id`, `asset_id`, `scene_id`, `role`, anchor, offset, duration, source trim, playback rate và chính sách khi cảnh thay đổi độ dài. Audio thêm bus/gain/fade/loop/ducking; visual thêm z-order/fit/transform/opacity/blend/keyframes. Đây là hợp đồng đích; capability gate phải báo những trường renderer chưa thực thi.

Ví dụ mô tả (không phải JSON có thể truyền thẳng vào Flow3): asset `sfx_whoosh_01` nằm ở `audio/sfx/whoosh.wav`; cue `cue_scene03_title` dùng asset đó khi title cảnh 03 xuất hiện, lệch +0.08 giây, gain -10 dB. Cùng file có thể được cue khác tham chiếu ở cảnh 06.

Mỗi hiệu ứng là một preset ID + version + tham số + danh sách dependency. Không có file âm thanh hay font tương ứng thì không được đánh dấu gói đã đủ.

## 4. Timeline chuẩn và bridge

Timeline gốc lưu thời gian theo cảnh và anchor có ngữ nghĩa: scene_start, scene_end, caption/word ID, animation_start hoặc beat ID. Timing từ preview là estimated. Không chỉ lưu phần trăm toàn video làm nguồn chân lý.

Luồng biên dịch trên Kaggle:

1. Validate snapshot, engine version, hash, đường dẫn và capability.
2. Tạo/chọn giọng cuối theo scene/speaker; kiểm tra đủ segment và đo duration.
3. Reflow scene theo speech thật, giữ những mốc người dùng khóa; quy định rõ thiếu footage thì loop/freeze/đổi asset hay báo lỗi. Không tự tăng tốc lời hoặc cắt mất lời.
4. Align chữ với audio cuối nếu cần word-level; trường hợp chưa align phải ghi estimated, không gắn nhãn karaoke chính xác.
5. Resolve anchor và cue, ghép video nền với trim/speed/fit đã duyệt.
6. Sinh flow2_package.json và flow3.project.v2 cho runtime hiện tại.
7. Render một đoạn kiểm tra → QC → render cuối → báo cáo phiên bản và những sai khác với preview.

| Trường nguồn | Đầu ra bridge |
|---|---|
| media, trim_in, playback_rate | bước ghép working video, không trông chờ decor layer làm montage |
| narration và speaker | final_lines text_target/speaker_id và cấu hình voice |
| duration sau reflow | duration_ms và start_ms/end_ms của event |
| tỷ lệ và resolution | video_width/video_height + canvas |
| overlay cue | image/video tracks với z, visibility, keyframes |
| nhạc/SFX | studio_audio sau khi resolve đường dẫn và cue |
| subtitle style | ánh xạ theo capability FFmpeg; không copy tên effect rồi mặc định tương đương |

Bridge đặt rõ timeline_mode=working_video và preprocess_speed=1.0 cho montage không bị thay tốc độ. Thời gian Flow3 theo phần trăm chỉ được tính sau khi chốt tổng duration: `t_pct = 100 * t_seconds / total_seconds`.

Điểm bắt buộc sửa khi triển khai: đường nhận audio cuối/precomputed segment và chế độ không sinh lại TTS. Tham số reference_audio hiện là đầu vào cho synthesis, không phải file narration cuối. Nếu tạo voice ở bước 2 rồi để Flow3 tạo lại ở bước 7 thì mất đồng bộ và có thể phát sinh chi phí hai lần. Không dùng mock_silent để giả là đã render final có giọng.

Dài hạn có thể thêm importer nhận project pipeline trực tiếp. Ngắn hạn bridge giữ Flow2 contract để hạn chế sửa sâu engine; đây là file tương thích, không có nghĩa cần chạy OCR/dịch qua Flow1/Flow2 cho kịch bản đã có.

## 5. Quy tắc dataset và runtime

- Snapshot input chỉ đọc từ `/kaggle/input/<dataset>/...`; config đã resolve, TTS mới, video nền, cache, preview và output viết vào `/kaggle/working/<project_id>/...`. File tạm ở `/tmp`.
- Luôn chỉ định output-dir; mặc định xuất cạnh flow2_dir không phù hợp khi flow2_dir nằm trong dataset chỉ đọc.
- Không phụ thuộc khả năng chèn asset vào input khi job đang chạy. Thiếu asset bắt buộc: dừng trước render, bổ sung bản xuất/dataset version rồi dùng phiên bản đó cho lần chạy tiếp theo.
- Có thể tách engine dataset dùng chung và project dataset tự đủ media; engine/version phải được khóa trong project. Không để project trỏ vào thư viện media cá nhân rải rác.
- Nếu offline, các dependency/model cần thiết phải có sẵn và đã kiểm thử trên Linux. Không mang Windows venv/node_modules sang Kaggle. Chế độ online cài đặt riêng, có log và phiên bản; không mặc định Internet luôn bật.
- Dùng secret của môi trường hoặc biến môi trường, không đưa gemini.txt, .env, token, credentials vào snapshot. Lọc trường source_file đường dẫn máy local khỏi bản bàn giao khi không cần.
- Không tự upload/publish dataset trong bước nghiên cứu. Trước upload kiểm tra phạm vi và quyền riêng tư của toàn gói.
- Lưu output/version hoặc tải kết quả về, không coi working là kho lưu trữ bền vững.

Lưu ý uploader: Kaggle CLI tài liệu hiện ghi dir-mode mặc định là skip khi tạo dataset. Phải chọn cách bảo toàn cây thư mục rõ ràng hoặc dùng archive dự án rồi giải nén an toàn vào working; kiểm tra file listing/hash sau nạp. Không chỉ upload thư mục gốc rồi mặc định các thư mục SFX/layer đã đi theo.
Nguồn: https://github.com/Kaggle/kaggle-cli/blob/main/docs/datasets.md

## 6. Gate trước khi bấm xuất và trước render

Hai trạng thái riêng: `package_ready` (đủ dependency đầu vào) và `render_ready` (đã có timing/voice cuối và môi trường phù hợp). Có thể package_ready trong khi voice cuối còn cần sinh trên Kaggle.

Preflight phải kiểm tra:

- Mọi cue/effect/font tham chiếu asset tồn tại, hash đúng, không trùng ID; asset bắt buộc không chỉ có URL.
- Đường dẫn nằm trong project root, không traversal, không symlink thoát root; unpack archive an toàn.
- Không lọt secret, đường dẫn tuyệt đối máy local hoặc dependency ngoài gói không khai báo.
- Trim/duration hợp lệ; rate hữu hạn dương; cue có anchor giải được; phát hiện speech chồng/cắt và vùng trống.
- Hiệu ứng được renderer hỗ trợ hoặc tiền xử lý có khai báo; không âm thầm bỏ layer hay đổi style.
- Font đúng family/glyph tiếng Việt; alpha/codec/channel/sample rate kiểm tra bằng probe và mẫu dựng thật.
- Audio mix không thiếu bus bắt buộc; có giới hạn peak và phép đo loudness, không coi limiter là mastering đầy đủ.
- Báo cáo tách trạng thái export/compile/render/QC; lỗi không được biểu diễn bằng một chuỗi qc_passed trong trường lỗi.

## 7. Những khả năng chưa được phép hứa

- Nhánh FFmpeg decor hiện không tương đương editor đa track đầy đủ: text/shape/audio track không đi qua project_to_legacy_layers như image/video.
- Rotation không được thực thi tương đương trong FFmpeg animation; phải báo unsupported hoặc xử lý riêng.
- studio_audio đã hỗ trợ start/gain/loop; trim/fade/ducking cần preprocess hoặc triển khai, không thêm trường JSON rồi coi là xong.
- Video overlay cần kiểm thử phase khi xuất hiện muộn: chỉ enable theo thời gian không đảm bảo source bắt đầu ở frame đầu tại cue.
- Subtitle cuối nằm trên decor trong graph hiện tại; z-order tùy ý giữa text và layer chưa được đảm bảo.
- Preview local Remotion và FFmpeg/libass không mặc định giống từng pixel; nghiệm thu bằng đoạn khó có cùng timeline và style mapping.

## 8. Thứ tự triển khai đề xuất

1. Manifest + cue schema + validator + export dependency closure; thêm vai trò và bảng cảnh sử dụng trong giao diện hiện có.
2. Bridge build working video/Flow2 package/Flow3 project; mở đường nhận audio cuối không synth lại; strict mode báo thiếu thay vì bỏ qua.
3. Bộ mẫu 3 cảnh có video/ảnh, voice, nhạc, SFX lặp, overlay alpha, font Việt; kiểm tra reflow và chuyển project root sang đường dẫn khác.
4. Chạy offline/no-network từ snapshot ở root mới; thử thiếu file/hash sai/unsupported effect/voice dài.
5. Nghiệm thu phiên Kaggle sạch: preview ngắn, video cuối, probe, nghe/xem và QC; lưu engine hash, dataset version, thời gian và tài nguyên đo thực.

Chỉ sau bước 5 mới gọi là tích hợp chạy trên Kaggle. Bản nghiên cứu này không thay đổi Flow3, không tạo video và không xác nhận các test cũ đang pass.
