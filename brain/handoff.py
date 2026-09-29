"""Tạo Handoff Spec cho Flow1/Flow2/Flow3.
Bổ sung các trường mà Flow3 yêu cầu vào scenes.json + preview_profile.json + handoff.json:
    - format: "9:16" / "16:9" / "1:1"
    - frame_rate: 24 / 30 / 60
    - tts_profile: "male_young" / "female_warm" / ...
    - working_video: path tới video nền (Pexels/Pixabay stock)
    - voice_resolution: voice_profile đã chốt cho từng speaker

Bổ sung audio thật (Gemini TTS) cho các cảnh vào audio/.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_FRAME_RATE = 30
DEFAULT_TTS_PROFILE = "male_young"


def patch_project_for_flow3(project_dir: Path,
                            aspect: Optional[str] = None,
                            frame_rate: int = DEFAULT_FRAME_RATE,
                            tts_profile: str = DEFAULT_TTS_PROFILE,
                            working_video: Optional[Path] = None) -> Path:
    """Bổ sung field cho scenes.json + preview_profile.json + handoff.json để Flow3."""
    project_dir = Path(project_dir)
    if aspect is None:
        # The project/profile owns the canvas. This adapter must not silently
        # force a format when called without an explicit override.
        for name in ("brief.json", "preview_profile.json", "handoff.json"):
            candidate = project_dir / name
            if not candidate.is_file():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                aspect = payload.get("aspect_ratio") or payload.get("format")
            except (OSError, ValueError, TypeError):
                aspect = None
            if aspect:
                break
        aspect = aspect or "16:9"
    if aspect not in ("9:16", "16:9", "1:1"):
        raise ValueError("Tỉ lệ Flow3 phải là 9:16, 16:9 hoặc 1:1.")
    scenes_path = project_dir / "scenes.json"
    if not scenes_path.is_file():
        logger.warning("Không tìm thấy scenes.json trong %s — bỏ qua patch.", project_dir)
        return project_dir

    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    if isinstance(scenes, list):
        for s in scenes:
            s.setdefault("format", aspect)
            s.setdefault("frame_rate", frame_rate)
            s.setdefault("tts_profile", tts_profile)
            s.setdefault("voice_resolution", {
                "preset": _voice_preset_for_text(s.get("narration", "")),
                "tts_backend": "gemini",
                "speed": 1.0,
                "pitch": 0.0,
            })
        scenes_path.write_text(json.dumps(scenes, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    # preview_profile.json
    pp_path = project_dir / "preview_profile.json"
    if pp_path.is_file():
        pp = json.loads(pp_path.read_text(encoding="utf-8"))
        pp.setdefault("format", aspect)
        pp.setdefault("frame_rate", frame_rate)
        pp.setdefault("tts_profile", tts_profile)
        if working_video is not None:
            # working_video dùng để Flow3 phát hiện video nền nếu SAU này đẩy lên Kaggle
            pp["working_video"] = str(working_video)
        pp_path.write_text(json.dumps(pp, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    # handoff.json
    handoff_path = project_dir / "handoff.json"
    if handoff_path.is_file():
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        handoff.setdefault("format", aspect)
        handoff.setdefault("frame_rate", frame_rate)
        handoff.setdefault("tts_profile", tts_profile)
        if working_video is not None:
            handoff["working_video"] = str(working_video)
        # Đánh dấu cảnh thiếu audio nhưng đã có Gemini TTS request sinh audio rồi
        # missing_audio sẽ là [] nếu audio được tạo trong bước tiếp theo.
        handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    logger.info("✅ Đã patch Flow3 spec cho %s: %s/%dfps/tts=%s",
                project_dir.name, aspect, frame_rate, tts_profile)
    return project_dir


def _voice_preset_for_text(text: str) -> str:
    """Chọn voice preset theo từ khoá đơn giản."""
    lower = (text or "").lower()
    if "ổng" in text or "ông " in text or "bà" in text or "sếp" in text:
        return "male_warm"
    if "cô " in text or "chị" in text or "nữ" in text:
        return "female_warm"
    if any(w in lower for w in ["tập cận bình", "xi jinping"]):
        return "male_power"
    if "tổng thống mỹ" in lower or "phát biểu" in lower:
        return "male_neutral"
    return DEFAULT_TTS_PROFILE


def fill_missing_audio(project_dir: Path, api_keys: list[str]) -> int:
    """Sinh file audio MP3/WAV cho các cảnh bị missing_audio.
    Dùng synthesize() của brain.tts (Gemini only). Trả số cảnh sinh được."""
    from .tts import synthesize
    project_dir = Path(project_dir)
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    scenes_path = project_dir / "scenes.json"
    if not scenes_path.is_file():
        return 0
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    handoff_path = project_dir / "handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8")) if handoff_path.is_file() else {}

    if not isinstance(scenes, list) or not scenes:
        return 0

    generated = 0
    missing = list(handoff.get("missing_audio") or [])
    for s in scenes:
        if not isinstance(s, dict):
            continue
        sid = s.get("scene_id", "")
        narration = (s.get("narration") or "").strip()
        if not sid or not narration:
            continue
        # Bỏ qua nếu audio đã tồn tại (MP3 hoặc WAV)
        mp3_path = audio_dir / f"{sid}.mp3"
        wav_path = audio_dir / f"{sid}.wav"
        if mp3_path.is_file() and mp3_path.stat().st_size > 0:
            if sid in missing:
                missing.remove(sid)
            continue
        if wav_path.is_file() and wav_path.stat().st_size > 0:
            convert_audio(wav_path, mp3_path)
            if sid in missing:
                missing.remove(sid)
            continue

        # Sinh audio từ Gemini TTS
        out = synthesize(narration, wav_path, api_keys=api_keys)
        if out is not None and out.is_file():
            convert_audio(wav_path, mp3_path)
            logger.info("✅ Gem TTS: %s (%s)", sid, out.name)
            if sid in missing:
                missing.remove(sid)
            generated += 1
        else:
            logger.warning("⚠️ TTS thất bại cảnh %s — bỏ qua.", sid)

    # Cập nhật lại missing_audio
    if handoff_path.is_file():
        handoff["missing_audio"] = missing
        handoff["final_voiceover_required"] = bool(missing)
        handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    return generated


def convert_audio(wav_path: Path, mp3_path: Path) -> bool:
    """Convert WAV → MP3 bằng FFmpeg (nếu có)."""
    import subprocess
    if not wav_path.is_file():
        return False
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path),
             "-codec:a", "libmp3lame", "-b:a", "128k", str(mp3_path)],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0 and mp3_path.is_file():
            try:
                wav_path.unlink()
            except OSError:
                pass
            return True
    except Exception:
        pass
    return False


def write_media_manifest(project_dir: Path) -> None:
    """Tạo media_manifest.json (Flow2/Flow3 đọc) — mô tả tất cả file media."""
    project_dir = Path(project_dir)
    media_root = project_dir / "media"
    if not media_root.is_dir():
        return

    items = []
    for f in sorted(media_root.iterdir()):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        kind = "video" if ext in {".mp4", ".mov", ".webm"} else "image"
        items.append({
            "filename": f.name,
            "kind": kind,
            "size_bytes": f.stat().st_size,
            "source": "local_stock",
            "license": "Pexels/Pixabay Commercial Free",
        })
    (project_dir / "media_manifest.json").write_text(
        json.dumps({"media": items, "count": len(items)},
                  ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
