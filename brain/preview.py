"""Dựng timeline preview (kiểu CapCut, chưa render) từ một project handoff.

Đọc project_<id>/ (brief.json, scenes.json, assets.jsonl, audio/, media/) và
trả về danh sách các "khối" nối tiếp nhau theo thời gian, mỗi khối gắn:
    - 1 asset đại diện (ảnh hoặc keyframe giữa của video)
    - phụ đề = narration của scene
    - audio (nếu có scene_<id>.mp3)
Thứ tự & thời lượng lấy từ scenes.json (estimated_duration_sec).

Đây là "bộ khung" để xem trước trên desktop app trước khi đẩy lên Colab/edit
render thật — KHÔNG trộn file, KHÔNG tạo video.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
VID_EXT = (".mp4", ".mov", ".webm", ".mkv", ".avi")


def inspect_visual_quality(path: str | Path) -> dict:
    """Cheap preview QC. Warnings are evidence for review, not semantic judgment."""
    media = Path(path)
    result = {"width": 0, "height": 0, "dominant_color_ratio": None, "warnings": []}
    if media.suffix.lower() not in IMG_EXT:
        return result
    try:
        from PIL import Image
        with Image.open(media) as source:
            image = source.convert("RGB")
            result.update(width=image.width, height=image.height)
            resampling = getattr(Image, "Resampling", Image).BILINEAR
            sample = image.resize((64, 64), resampling)
            colors = sample.quantize(colors=32).getcolors(maxcolors=4096) or []
            dominant = max((count for count, _ in colors), default=0) / 4096
            result["dominant_color_ratio"] = round(dominant, 4)
            if dominant >= 0.985:
                result["warnings"].append(
                    "Ảnh gần như một màu; có thể là placeholder/chroma hoặc asset chưa hoàn thiện.")
            if min(image.width, image.height) < 480:
                result["warnings"].append("Độ phân giải thấp; cần duyệt trước khi đưa lên máy render.")
    except Exception as exc:
        result["warnings"].append(f"Không đọc được ảnh: {exc}")
    return result


def load_project(project_dir: str | Path) -> dict:
    """Đọc toàn bộ project handoff thành 1 dict chuẩn để preview."""
    p = Path(project_dir)
    if not p.is_dir():
        raise FileNotFoundError(f"không tìm thấy project: {p}")

    brief = {}
    if (p / "brief.json").exists():
        brief = json.loads((p / "brief.json").read_text(encoding="utf-8"))

    scenes = []
    if (p / "scenes.json").exists():
        scenes = json.loads((p / "scenes.json").read_text(encoding="utf-8"))

    assets: dict[str, dict] = {}
    if (p / "assets.jsonl").exists():
        for line in (p / "assets.jsonl").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                a = json.loads(line)
                assets[a["asset_id"]] = a
            except (json.JSONDecodeError, KeyError):
                continue

    audio_dir = p / "audio"
    audio = {f.stem: str(f) for f in sorted(audio_dir.iterdir())
             if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")} if audio_dir.is_dir() else {}
    for scene in scenes:
        if scene.get('reference_audio'):
            path = (p / scene['reference_audio']).resolve()
            path.relative_to(p.resolve())
            if path.is_file():
                audio[scene['scene_id']] = str(path)

    return {
        "dir": p,
        "brief": brief,
        "scenes": scenes,
        "assets": assets,
        "audio": audio,
    }


def _resolve_media(asset: dict, project_dir: Path) -> Optional[Path]:
    """Tìm file ảnh/video thật của asset trong project/media/ hoặc source_file."""
    # 1) file đã copy vào project/media/
    mf = asset.get("media_file")
    if mf:
        cand = project_dir / "media" / mf
        if cand.exists():
            return cand
    # 2) source_file gốc (nếu còn)
    sf = asset.get("source_file")
    if sf and Path(sf).exists():
        return Path(sf)
    return None


def _keyframe(video: Path, t: float, out: Path, max_width: int = 960) -> Optional[Path]:
    """Trích 1 khung tại giây t từ video bằng ffmpeg."""
    args = ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", f"scale='min({max_width},iw)':-2",
            "-q:v", "3", str(out)]
    subprocess.run(args, capture_output=True)
    if out.exists() and out.stat().st_size > 0:
        return out
    return None


def _probe_duration(video: Path) -> float:
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        return float(probe.stdout.strip())
    except Exception:
        return 0.0


def representative_frame(asset: dict, project_dir: Path,
                         cache_dir: Path | None = None) -> Optional[Path]:
    """Trả đường dẫn ảnh đại diện của asset (ảnh gốc, hoặc keyframe video)."""
    media = _resolve_media(asset, project_dir)
    if media is None:
        return None
    if media.suffix.lower() in IMG_EXT:
        return media
    if media.suffix.lower() in VID_EXT:
        cache = cache_dir or (project_dir / ".preview_cache")
        cache.mkdir(parents=True, exist_ok=True)
        key = cache / f"{asset['asset_id']}.jpg"
        if key.exists():
            return key
        dur = _probe_duration(media)
        t = dur * 0.5 if dur > 0 else 0.0
        return _keyframe(media, t, key)
    return None


def build_timeline(project: dict, cache_dir: Path | None = None) -> list[dict]:
    """Dựng danh sách khối nối tiếp nhau theo scenes.json.

    Mỗi khối: {scene_id, start, end, duration, media, subtitle, audio, status,
               visual_intent, asset_ids, on_screen_text}
    """
    p: Path = project["dir"]
    scenes = project["scenes"]
    assets = project["assets"]
    audio = project["audio"]
    cache = cache_dir or (p / ".preview_cache")

    timeline: list[dict] = []
    cursor = 0.0
    for s in scenes:
        sid = s.get("scene_id", "")
        dur = float(s.get("estimated_duration_sec") or 5.0)
        if dur <= 0:
            dur = 5.0

        # chọn asset đại diện: asset đầu tiên trong asset_ids có file thật
        media: Optional[Path] = None
        used_asset_id = ""
        for aid in (s.get("asset_ids") or []):
            a = assets.get(aid)
            if not a:
                continue
            media = _resolve_media(a, p)
            if media:
                used_asset_id = aid
                break

        subtitle = (s.get("narration") or "").strip()
        quality = inspect_visual_quality(media) if media else {"warnings": []}
        timeline.append({
            "scene_id": sid,
            "start": cursor,
            "end": cursor + dur,
            "duration": dur,
            "media": str(media) if media else "",
            "asset_id": used_asset_id,
            "subtitle": subtitle,
            "on_screen_text": s.get("on_screen_text", "") or "",
            "visual_intent": s.get("visual_intent", "") or "",
            "sfx_cues": s.get("sfx_cues", []),
            "audio": audio.get(sid, "") if sid else "",
            "status": s.get("status", "needs_assets"),
            "visual_quality": quality,
            "visual_warnings": quality.get("warnings", []),
        })
        cursor += dur

    return timeline


def timeline_summary(timeline: list[dict]) -> dict:
    """Tóm tắt nhanh để log/UI: tổng thời lượng, số cảnh, thiếu asset/audio."""
    total = timeline[-1]["end"] if timeline else 0.0
    return {
        "scenes": len(timeline),
        "total_duration_sec": round(total, 1),
        "with_media": sum(1 for c in timeline if c["media"]),
        "with_audio": sum(1 for c in timeline if c["audio"]),
        "with_subtitle": sum(1 for c in timeline if c["subtitle"]),
        "asset_warnings": sum(1 for c in timeline if c.get("visual_warnings")),
    }
