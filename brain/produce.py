"""Orchestrator end-to-end: Brief -> Research -> Script -> Vision -> TTS -> Handoff.

Đây là lớp điều phối, không chứa logic nặng — mỗi khâu gọi đúng module brain.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import models
from .clip import extract_keyframes
from .project import create_project
from .scenes import Scene, save_scenes
from .tts import synthesize_scenes
from .vision import describe_asset, match_scene


def describe_assets(asset_paths: list[str | Path], api_keys: str | list[str],
                    cache_path: str | Path | None = None) -> dict[str, dict]:
    """Quét mô tả cho một danh sách asset (ảnh/video) bằng Groq vision.

    asset_paths: đường dẫn file. api_keys: 1 key hoặc list key (xoay vòng).
    cache_path: file json để tránh quét lại.
    Trả về {asset_id: mô tả}.
    """
    cache: dict = {}
    if cache_path and Path(cache_path).exists():
        cache = json.loads(Path(cache_path).read_text(encoding="utf-8"))

    out: dict[str, dict] = {}
    for p in asset_paths:
        path = Path(p)
        aid = path.stem
        if aid in cache:
            out[aid] = cache[aid]
            continue
        desc = describe_asset(path, api_keys)
        out[aid] = desc
        cache[aid] = desc
        if cache_path:
            Path(cache_path).write_text(
                json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def run_production(brief: dict, research_md: str, script_md: str,
                   scenes: list[Scene], asset_paths: list[str | Path],
                   cfg: dict, out_root: str | Path,
                   project_id: str | None = None) -> dict:
    """Chạy đủ 4 giai đoạn và trả về summary + đường dẫn project."""
    groq_keys = models.load_groq_keys(cfg)
    gemini_keys = models.load_gemini_keys(cfg)
    groq_key = groq_keys[0] if groq_keys else ""

    # 1. Vision scan asset
    asset_desc: dict[str, dict] = {}
    if asset_paths and groq_keys:
        asset_desc = describe_assets(asset_paths, groq_keys)

    # 2. Match asset vào scene
    for s in scenes:
        if s.status == "ready":
            continue
        if not groq_key:
            # không có key -> giữ nguyên needs_assets
            continue
        aid = match_scene(s.to_dict(), asset_desc, groq_key)
        if aid:
            s.asset_ids.append(aid)
            s.status = "ready"
        else:
            s.status = "needs_ai_gen"

    assets = [{**asset_desc.get(Path(p).stem, {}), "asset_id": Path(p).stem,
               "source_file": str(Path(p).resolve())} for p in asset_paths]
    # Local TTS is optional reference audio, not a final-production requirement.
    audio_map = {}
    if cfg.get("ai", {}).get("preview_tts", False) and gemini_keys:
        audio_map = synthesize_scenes(scenes, Path(out_root) / "_audio_tmp", gemini_keys)
    proj = create_project(brief, research_md, script_md, scenes, assets,
                          out_root, project_id, audio_map=audio_map)

    # chuyển audio vào project/audio/
    for scene_id, ap in audio_map.items():
        dest = proj / "audio" / f"{scene_id}{Path(ap).suffix}"
        try:
            dest.write_bytes(Path(ap).read_bytes())
        except Exception:
            pass

    save_scenes(scenes, proj / "scenes.json")
    from .profile import save_profile
    save_profile(proj, [s.to_dict() for s in scenes])

    return {
        "project": str(proj),
        "scenes": len(scenes),
        "ready": sum(1 for s in scenes if s.status == "ready"),
        "needs_ai_gen": sum(1 for s in scenes if s.status == "needs_ai_gen"),
        "assets_scanned": len(asset_desc),
        "audio": len(audio_map),
        "groq_keys": len(groq_keys),
        "gemini_keys": len(gemini_keys),
    }
