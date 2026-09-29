"""Brain layer: nối kịch bản -> vision match -> TTS -> đóng gói project.

Các module con:
    models   - registry model ID (Groq/Gemini) + nạp API key (nhiều key)
    keypool  - xoay vòng key + fallback + cooldown chống khóa lưu lượng
    clip     - trích keyframe từ video bằng ffmpeg
    vision   - quét ảnh/keyframe bằng Groq qwen3.8-27b (JSON mode)
    scenes   - schema Scene + đọc/ghi scenes.json + dựng từ script.md
    tts      - giọng đọc CHỈ Gemini TTS (fail thì bỏ qua, editor lồng tiếng)
    project  - đóng gói project_<id>/ theo chuẩn handoff
    produce  - orchestrator end-to-end
"""
from .models import (
    GROQ_VISION_MODEL,
    GEMINI_FLASH_MODELS,
    GEMINI_TTS_MODEL,
    GEMINI_TTS_LITE_MODEL,
    load_groq_key,
    load_groq_keys,
    load_gemini_key,
    load_gemini_keys,
)

__all__ = [
    "GROQ_VISION_MODEL",
    "GEMINI_FLASH_MODELS",
    "GEMINI_TTS_MODEL",
    "GEMINI_TTS_LITE_MODEL",
    "load_groq_key",
    "load_groq_keys",
    "load_gemini_key",
    "load_gemini_keys",
]
