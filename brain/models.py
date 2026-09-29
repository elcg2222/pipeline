"""Registry model ID + nạp API key (nhiều key + fallback) từ env/config/file.

Mọi tên model đều nằm ở đây để sửa 1 chỗ là đúng toàn pipeline.
Key được đọc theo thứ tự:
    1. env var chuẩn
    2. config.yaml `ai.<provider>.api_key` (có thể là chuỗi cách nhau bởi ',' hoặc '\n')
    3. file key (ai.<provider>.key_file, hoặc ~/Downloads/<provider>.txt)

Không bao giờ in key ra màn hình.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ---- Groq (vision + text) ----
GROQ_VISION_MODEL = "qwen/qwen3.8-27b"      # multimodal 27B, vision, JSON mode, 131k ctx
GROQ_REASONING_MODEL = "qwen-qwq-32b"       # dự phòng suy luận sâu nếu cần

# ---- Gemini (long context + TTS) ----
GEMINI_FLASH_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]
GEMINI_TTS_MODEL = "gemini-3.8-flash-tts"
GEMINI_TTS_LITE_MODEL = "gemini-3.8-flash-lite-tts"

# thứ tự env var được chấp nhận cho từng nhà cung cấp
_GROQ_ENV = ("GROQ_API_KEY",)
_GEMINI_ENV = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY")


def _split_keys(raw: str) -> list[str]:
    """Tách chuỗi key (phân tách bởi newline hoặc dấu phẩy) thành list key sạch."""
    out = []
    for part in raw.replace(",", "\n").split("\n"):
        k = part.strip()
        if k:
            out.append(k)
    return out


def _read_key_file(path: str | Path) -> list[str]:
    """Đọc file key: bỏ dòng trống và dòng comment (#)."""
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def load_groq_keys(cfg: dict | None = None) -> list[str]:
    """Trả về DANH SÁCH key Groq khả dụng, đã loại trùng."""
    keys: list[str] = []
    env = os.environ.get("GROQ_API_KEY")
    if env:
        keys += _split_keys(env)
    if cfg:
        ai = cfg.get("ai", {}).get("groq", {}) or {}
        if ai.get("api_key"):
            keys += _split_keys(str(ai["api_key"]))
        if ai.get("key_file"):
            keys += _read_key_file(ai["key_file"])
    # mặc định tìm ~/Downloads/groq.txt
    for cand in (Path.home() / "Downloads" / "groq.txt",):
        keys += _read_key_file(cand)
    # loại trùng, giữ thứ tự
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def load_gemini_keys(cfg: dict | None = None) -> list[str]:
    keys: list[str] = []
    for e in _GEMINI_ENV:
        v = os.environ.get(e)
        if v:
            keys += _split_keys(v)
    if cfg:
        ai = cfg.get("ai", {}).get("gemini", {}) or {}
        if ai.get("api_key"):
            keys += _split_keys(str(ai["api_key"]))
        if ai.get("key_file"):
            keys += _read_key_file(ai["key_file"])
    for cand in (Path.home() / "Downloads" / "gemini.txt",):
        keys += _read_key_file(cand)
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


# --- API tương thích cũ (trả về key đầu tiên) ---
def load_groq_key(cfg: dict | None = None) -> str:
    keys = load_groq_keys(cfg)
    return keys[0] if keys else ""


def load_gemini_key(cfg: dict | None = None) -> str:
    keys = load_gemini_keys(cfg)
    return keys[0] if keys else ""


def status(cfg: dict | None = None) -> dict:
    """Báo cáo cấu hình AI hiện tại (không lộ key)."""
    return {
        "groq": {
            "vision_model": GROQ_VISION_MODEL,
            "keys": len(load_groq_keys(cfg)),
        },
        "gemini": {
            "flash_models": GEMINI_FLASH_MODELS,
            "tts_model": GEMINI_TTS_MODEL,
            "tts_lite_model": GEMINI_TTS_LITE_MODEL,
            "keys": len(load_gemini_keys(cfg)),
        },
    }
