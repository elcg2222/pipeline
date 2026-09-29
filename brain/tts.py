"""Giọng đọc: CHỈ dùng Gemini TTS (không fallback edge-tts).

Quyết định của user: trên máy local này chỉ gọi Gemini làm TTS. Nếu Gemini
fail (quota/hết key/sai key) thì KHÔNG sinh audio — bỏ qua cảnh đó, để máy
edit/Colab lồng tiếng sau. Không dùng edge-tts hay bất kỳ TTS thay thế nào.

CHỐNG KHÓA LƯU LƯỢNG GEMINI:
    - Xoay vòng nhiều key qua KeyPool, không dồn 1 key.
    - Key báo quota/rate-limit -> cooldown dài (không thử lại ngay).
    - Khi TẤT CẢ key chết -> trả None (bỏ qua), KHÔNG cố gọi thêm lần nữa.
    - Delay jitter giữa các lần gọi.
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import re
import wave
from typing import Optional

from .keypool import KeyPool, retry_with_pool
from .models import GEMINI_TTS_MODEL

_pool_cache: dict[str, KeyPool] = {}


def _get_pool(api_keys: list[str]) -> KeyPool:
    if not api_keys:
        raise RuntimeError("không có Gemini API key")
    sig = api_keys[0]
    if sig not in _pool_cache:
        # cooldown dài (120s) để tránh chạm ngưỡng quota liên tục
        _pool_cache[sig] = KeyPool(api_keys, cooldown_seconds=120.0,
                                   max_consecutive_failures=1,
                                   base_delay=1.5)
    return _pool_cache[sig]


def _gemini_tts(text: str, out_path: Path, api_key: str,
                voice_name: str = "Aoede", tts_model: str = GEMINI_TTS_MODEL) -> bool:
    """Sinh audio qua Gemini TTS. Trả True nếu thành công và ghi file."""
    try:
        available = importlib.util.find_spec("google.genai")
    except ModuleNotFoundError:
        available = None
    if available is None:
        raise RuntimeError("Cài TTS SDK: python -m pip install google-genai")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=90000))
    resp = client.models.generate_content(
        model=tts_model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    ),
                ),
            ),
        ),
    )
    for part in resp.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            mime = (part.inline_data.mime_type or "").lower()
            data = part.inline_data.data
            if "pcm" in mime or "l16" in mime:
                rate = re.search(r"rate=(\d+)", mime)
                with wave.open(str(out_path), "wb") as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(int(rate.group(1)) if rate else 24000)
                    audio.writeframes(data)
            elif "wav" in mime:
                out_path.write_bytes(data)
            else:
                raise ValueError(f"Định dạng TTS chưa hỗ trợ: {mime}")
            return True
    return False


def synthesize(text: str, out_path: str | Path,
               api_keys: str | list[str] = "",
               tts_model: str = GEMINI_TTS_MODEL) -> Optional[Path]:
    """Đọc 1 đoạn văn thành audio bằng Gemini TTS.

    api_keys: 1 key (str) hoặc list key (xoay vòng + cooldown).
    Trả về đường dẫn file đã ghi, hoặc None nếu Gemini fail (KHÔNG fallback).
    """
    out = Path(out_path).with_suffix(".wav")
    out.parent.mkdir(parents=True, exist_ok=True)

    keys = [api_keys] if isinstance(api_keys, str) and api_keys else \
           (list(api_keys) if isinstance(api_keys, (list, tuple)) else [])
    keys = [k for k in keys if k]
    if not keys:
        return None

    try:
        if len(keys) == 1:
            ok = _gemini_tts(text, out, keys[0], voice_name="Aoede",
                             tts_model=tts_model)
        else:
            pool = _get_pool(keys)
            ok, _ = retry_with_pool(
                pool, lambda k: _gemini_tts(text, out, k, "Aoede", tts_model),
                max_rounds=len(keys),
            )
            ok = bool(ok)
        return out if ok else None
    except Exception:
        return None


def synthesize_scenes(scenes, audio_dir: str | Path,
                      api_keys: str | list[str] = "") -> dict[str, Path]:
    """Đọc narration của từng scene -> scene_<id>.mp3 (chỉ Gemini TTS).

    Cảnh nào Gemini fail thì bỏ qua (không có trong kết quả), để editor lồng
    tiếng sau. Trả map scene_id -> path (chỉ các cảnh thành công).
    """
    out = Path(audio_dir)
    out.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    for s in scenes:
        if not s.narration.strip():
            continue
        p = synthesize(s.narration, out / f"{s.scene_id}.wav", api_keys=api_keys)
        if p is not None:
            result[s.scene_id] = p
    return result
