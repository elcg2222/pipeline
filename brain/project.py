"""Đóng gói project_<id>/ theo đúng chuẩn handoff của PIPELINE_DIRECTION.md.

Thư mục:
    project_<id>/
      brief.json  research.md  script.md  scenes.json
      assets.jsonl  attribution.md  handoff.json
      audio/  media/
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from .srt import write_srt


def _write_json(path: Path, obj: dict):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _roadmap(project_id: str, brief: dict, scenes: list[dict]) -> str:
    ratio = brief["aspect_ratio"]
    return f"""# PROJECT ROADMAP — {project_id}

## Mục đích

Đây là thư mục bàn giao duy nhất của dự án. Agent viết kịch bản/chọn asset phải
đưa file thật vào thư mục này và cập nhật manifest; không chỉ ghi URL hoặc đường
dẫn máy cá nhân. Flow3/Kaggle đọc hồ sơ, không tự đoán ý nghĩa từ tên file.

## Canvas đã chốt

- Tỷ lệ: `{ratio}`
- Nguồn quyết định: `{brief.get('aspect_ratio_source', 'explicit_or_legacy')}`
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

- Số cảnh: {len(scenes)}
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
"""


def create_project(brief: dict, research_md: str, script_md: str,
                   scenes: list, assets: list[dict],
                   out_root: str | Path,
                   project_id: str | None = None,
                   audio_map: dict | None = None) -> Path:
    """Tạo gói project và ghi mọi file. Trả về đường dẫn thư mục project."""
    brief = dict(brief)
    if not brief.get("aspect_ratio"):
        brief["aspect_ratio"] = "16:9"
        brief["aspect_ratio_source"] = "legacy_fallback:16:9"
    if brief["aspect_ratio"] not in ("9:16", "16:9", "1:1"):
        raise ValueError("Project phải chốt tỷ lệ 9:16, 16:9 hoặc 1:1 trước khi tạo.")
    root = Path(out_root)
    root.mkdir(parents=True, exist_ok=True)
    if project_id is None:
        project_id = time.strftime("project_%Y%m%d_%H%M%S")
    proj = root / project_id
    proj.mkdir(parents=True, exist_ok=True)

    _write_json(proj / "brief.json", brief)
    (proj / "research.md").write_text(research_md, encoding="utf-8")
    (proj / "script.md").write_text(script_md, encoding="utf-8")

    scene_dicts = [s.to_dict() if hasattr(s, "to_dict") else s for s in scenes]
    _write_json(proj / "scenes.json", scene_dicts)
    (proj / "PROJECT_ROADMAP.md").write_text(
        _roadmap(project_id, brief, scene_dicts), encoding="utf-8")

    # subtitles.srt cho khâu render/edit
    write_srt(scenes, proj / "subtitles.srt")

    # assets.jsonl: mỗi dòng 1 asset (kèm media_file = đường dẫn trong project)
    media_dir = proj / "media"
    media_dir.mkdir(exist_ok=True)
    with (proj / "assets.jsonl").open("w", encoding="utf-8") as f:
        for a in assets:
            src = a.get("source_file")
            if src and Path(src).exists():
                try:
                    ext = Path(src).suffix
                    dest = media_dir / f"{a.get('asset_id', 'asset')}{ext}"
                    if not dest.exists():
                        shutil.copy2(src, dest)
                    a = {**a, "media_file": dest.name}
                except Exception:
                    pass
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    # attribution.md: gom nguồn + giấy phép
    attr_lines = ["# Attribution (nguồn & giấy phép)\n"]
    for a in assets:
        src = a.get("source_url", "") or a.get("provider", "")
        lic = a.get("license_id", "") or ""
        attr_lines.append(f"- {a.get('title', a.get('asset_id', ''))} — {src} ({lic})")
    (proj / "attribution.md").write_text("\n".join(attr_lines), encoding="utf-8")

    # handoff.json
    ready = all(s.get("status") == "ready" for s in scene_dicts)
    audio_map = audio_map or {}
    missing_audio = [s["scene_id"] for s in scene_dicts
                     if s.get("narration", "").strip() and s["scene_id"] not in audio_map]
    handoff = {
        "schema_version": 1,
        "project_id": project_id,
        "script_revision": 1,
        "aspect_ratio": brief["aspect_ratio"],
        "aspect_ratio_source": brief.get("aspect_ratio_source", "explicit_or_legacy"),
        "target_duration_sec": brief.get("target_duration_sec", 0),
        "scene_order": [s["scene_id"] for s in scene_dicts],
        "media_root": "media/",
        "subtitles_file": "subtitles.srt",
        "missing_assets": [s["scene_id"] for s in scene_dicts
                           if s.get("status") != "ready"],
        "missing_audio": missing_audio,  # cảnh có lời nhưng chưa có TTS -> editor lồng tiếng
        "status": "ready_for_edit" if ready else "needs_assets",
    }
    _write_json(proj / "handoff.json", handoff)

    (proj / "audio").mkdir(exist_ok=True)
    return proj
