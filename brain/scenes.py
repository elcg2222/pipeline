"""Schema Scene + đọc/ghi scenes.json + dựng cảnh thô từ script.md.

Scene đúng chuẩn PIPELINE_DIRECTION.md: mỗi cảnh có narration, visual_intent,
thời lượng dự kiến, source_ids, asset_ids, framing, on_screen_text, status.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Scene:
    scene_id: str
    chapter_id: str = ""
    narration: str = ""
    estimated_duration_sec: float = 5.0
    visual_intent: str = ""
    source_ids: list[str] = field(default_factory=list)
    asset_ids: list[str] = field(default_factory=list)
    trim_in: float = 0.0
    trim_out: float = 0.0
    framing: str = ""                 # 9:16 / 16:9 / square
    on_screen_text: str = ""
    text_effect: str = "fade"
    playback_rate: float = 1.0
    review_notes: str = ""
    match_method: str = ""
    match_reason: str = ""
    needs_visual_review: bool = True
    alternatives: list[str] = field(default_factory=list)
    status: str = "needs_assets"      # needs_assets | ready | needs_ai_gen

    def to_dict(self) -> dict:
        return asdict(self)


def save_scenes(scenes: list[Scene], path: str | Path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([s.to_dict() for s in scenes],
                            ensure_ascii=False, indent=2), encoding="utf-8")


def load_scenes(path: str | Path) -> list[Scene]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Scene(**d) for d in data]


def build_scenes_from_script(script_md: str, default_duration: float = 5.0) -> list[Scene]:
    """Tách script.md thành các cảnh theo tiêu đề `##` hoặc dòng `[SCENE]`.

    Đây chỉ là dựng thô để có khung; kịch bản thật do Hermes viết và lưu
    scenes.json trực tiếp.
    """
    scenes: list[Scene] = []
    chapter = ""
    # tách theo heading markdown
    blocks = re.split(r"(?m)^(#{1,3}\s+.+)$", script_md)
    cur_narration: list[str] = []
    cur_heading = ""

    def flush():
        nonlocal cur_narration, cur_heading
        if not cur_heading and not any(x.strip() for x in cur_narration):
            return
        text = "\n".join(cur_narration).strip()
        if text or cur_heading:
            scenes.append(Scene(
                scene_id=f"scene_{len(scenes) + 1:03d}",
                chapter_id=chapter or "main",
                narration=text,
                visual_intent=(cur_heading.lstrip("# ").strip()),
                estimated_duration_sec=default_duration,
            ))
        cur_narration = []
        cur_heading = ""

    for part in blocks:
        part = part.strip()
        if not part:
            continue
        if re.match(r"^#{1,3}\s+", part):
            level = len(part) - len(part.lstrip("#"))
            if level == 1:
                # chapter heading: chỉ đặt chapter, KHÔNG tạo scene
                chapter = part.lstrip("# ").strip()
                cur_heading = ""
                continue
            flush()
            cur_heading = part
        else:
            cur_narration.append(part)
    flush()
    return scenes
