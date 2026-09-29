"""Tạo file phụ đề .srt từ kịch bản (scenes) + thời lượng ước tính.

Dùng cho khâu render/edit ở Colab: mỗi scene -> 1 khối subtitle, thời điểm
nối tiếp nhau theo estimated_duration_sec. Colab chỉ cần đọc srt + scenes.json
là biết chèn text/ảnh/video vào đâu.
"""
from __future__ import annotations

from pathlib import Path


def _ts(seconds: float) -> str:
    """Giây -> SRT timestamp HH:MM:SS,mmm."""
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def scenes_to_srt(scenes: list, start_sec: float = 0.0) -> str:
    """Chuyển list Scene thành nội dung .srt.

    scenes: list[Scene] (hoặc dict có scene_id/narration/estimated_duration_sec).
    Thời gian nối tiếp nhau; cảnh không có narration bị bỏ qua.
    """
    lines: list[str] = []
    cursor = start_sec
    idx = 0
    for s in scenes:
        d = s.to_dict() if hasattr(s, "to_dict") else s
        text = (d.get("narration") or "").strip()
        dur = float(d.get("estimated_duration_sec") or 5.0)
        start = cursor
        end = cursor + dur
        cursor = end
        if not text:
            continue
        idx += 1
        lines.append(str(idx))
        lines.append(f"{_ts(start)} --> {_ts(end)}")
        lines.append(text)
        lines.append("")
        cursor = end
    return "\n".join(lines).rstrip("\n") + "\n"


def write_srt(scenes: list, path: str | Path, start_sec: float = 0.0) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(scenes_to_srt(scenes, start_sec), encoding="utf-8")
    return p
