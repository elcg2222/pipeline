"""Portable preview contract. Local audio is a reference, never final voiceover."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .preview import load_project, _resolve_media, inspect_visual_quality
from .srt import write_srt

EFFECTS = ("fade", "slide", "pop", "typewriter")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def save_profile(project_dir, scenes: list[dict], *, approved: bool = False) -> dict:
    """Preserve scene extensions, snapshot previous state, and rebuild derived files."""
    root = Path(project_dir).resolve()
    project = load_project(root)
    ratio = str(project["brief"].get("aspect_ratio") or "16:9")
    if ratio not in ("9:16", "16:9", "1:1"):
        raise ValueError("Tỉ lệ hỗ trợ: 9:16, 16:9, 1:1.")
    if not scenes:
        raise ValueError("Cần ít nhất một cảnh.")
    ids = [s["scene_id"] for s in scenes]
    if len(set(ids)) != len(ids):
        raise ValueError("scene_id không được trùng nhau.")
    for scene in scenes:
        duration = float(scene.get("estimated_duration_sec", 5))
        speed = float(scene.get("playback_rate", 1))
        if not math.isfinite(duration) or duration <= 0 or not math.isfinite(speed) or speed <= 0:
            raise ValueError("Thời lượng và tốc độ phải là số dương hữu hạn.")
        if scene.get("text_effect", "fade") not in EFFECTS:
            raise ValueError("Hiệu ứng chữ chưa được hỗ trợ.")
    old_path = root / "preview_profile.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
    revision = int(old.get("revision", 0)) + 1
    backup = root / "revisions" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup.mkdir(parents=True)
    for name in ("scenes.json", "preview_profile.json", "handoff.json", "subtitles.srt"):
        if (root / name).is_file():
            shutil.copy2(root / name, backup / name)
    packed = []
    missing = []
    quality_warnings = {}
    for scene in scenes:
        media = None
        for aid in scene.get("asset_ids", []):
            media = _resolve_media(project["assets"].get(aid, {}), root)
            if media:
                break
        rel = ""
        if media:
            media = media.resolve()
            try:
                rel = media.relative_to(root).as_posix()
            except ValueError:
                digest = hashlib.sha256(str(media).encode("utf-8")).hexdigest()[:16]
                dest = root / "media" / (digest + media.suffix.lower())
                dest.parent.mkdir(exist_ok=True)
                shutil.copy2(media, dest)
                rel = dest.relative_to(root).as_posix()
        else:
            missing.append(scene["scene_id"])
        if media:
            warnings = inspect_visual_quality(media).get("warnings", [])
            if warnings:
                quality_warnings[scene["scene_id"]] = warnings
        audio = project["audio"].get(scene["scene_id"])
        if scene.get('reference_audio'):
            reference = (root / scene['reference_audio']).resolve()
            reference.relative_to(root)
            if not reference.is_file():
                raise FileNotFoundError('Thiếu audio tham chiếu đã chọn.')
            audio = str(reference)
        packed.append({**scene, "media": rel,
                       "audio": Path(audio).relative_to(root).as_posix() if audio else "",
                       "text_effect": scene.get("text_effect", "fade")})
    profile = {
        "schema_version": 2, "revision": revision, "project_id": root.name,
        "purpose": "direction_preview", "audio_role": "reference_only",
        "final_voiceover_required": True,
        "review_status": "approved" if approved else "draft",
        "approved_at": datetime.now(timezone.utc).isoformat() if approved else None,
        "aspect_ratio": ratio,
        "aspect_ratio_source": project["brief"].get("aspect_ratio_source", "explicit_or_legacy"),
        "fps": 30, "scenes": packed, "missing_assets": missing,
        "asset_quality_warnings": quality_warnings,
        "editor_target": "kaggle", "timing_policy": "reflow_after_final_voiceover",
        "style_notes": project["brief"].get("style", ""),
    }
    # Preserve explicit editor choices added by older adapters; never preserve
    # arbitrary fields that could smuggle local configuration or secrets.
    for key in ("format", "frame_rate", "tts_profile", "soft_subtitles"):
        if key in old:
            profile[key] = old[key]
    handoff_path = root / "handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8")) if handoff_path.exists() else {}
    handoff.update(schema_version=2, preview_profile="preview_profile.json", revision=revision,
                   scene_order=ids, target_duration_sec=sum(float(s.get("estimated_duration_sec", 5)) for s in scenes),
                   missing_assets=missing, audio_role="reference_only", final_voiceover_required=True,
                   asset_quality_warnings=quality_warnings,
                   status=("needs_asset_review" if quality_warnings else
                           "approved_for_edit" if approved and not missing else "preview_draft"),
                   missing_audio=[s["scene_id"] for s in packed if s.get("narration") and not s["audio"]])
    write_json(root / "scenes.json", scenes)
    write_srt(scenes, root / "subtitles.srt")
    write_json(old_path, profile)
    write_json(handoff_path, handoff)
    return profile


def stage_remotion(project_dir, studio_dir, *, update_active=True) -> dict:
    """Only publish referenced media/audio, never configuration, keys or research."""
    root, studio = Path(project_dir).resolve(), Path(studio_dir).resolve()
    profile = json.loads((root / "preview_profile.json").read_text(encoding="utf-8"))
    token = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    public_root = studio / "public" / "projects" / token
    public_root.mkdir(parents=True, exist_ok=True)
    for scene in profile["scenes"]:
        for key in ("media", "audio"):
            if not scene.get(key):
                continue
            source = (root / scene[key]).resolve()
            relative = source.relative_to(root)  # reject path traversal / external paths
            target = public_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or source.stat().st_mtime_ns != target.stat().st_mtime_ns:
                shutil.copy2(source, target)
            scene[key] = f"projects/{token}/{relative.as_posix()}"
    if update_active:
        write_json(studio / "src" / "active-profile.json", profile)
    return profile
