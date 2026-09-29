"""Vision scanning & asset matching bằng Groq qwen3.8-27b.

Mỗi lần gọi tối đa 3 ảnh. Ảnh -> JSON mô tả (caption, OCR, vật thể, góc quay)
-> đối chiếu với `visual_intent` của từng Scene để chọn asset phù hợp.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from .clip import image_to_data_url
from .keypool import KeyPool, retry_with_pool
from .models import GROQ_VISION_MODEL

_pool_cache: dict[str, KeyPool] = {}


def _get_pool(api_keys: list[str]) -> KeyPool:
    """Một key pool cho một bộ key (cache theo key đầu tiên)."""
    if not api_keys:
        raise RuntimeError("không có Groq API key")
    sig = api_keys[0]
    if sig not in _pool_cache:
        _pool_cache[sig] = KeyPool(api_keys, cooldown_seconds=30.0)
    return _pool_cache[sig]

# Prompt chuẩn: buộc model trả JSON với đúng các khoá cần cho matching.
ANALYZE_PROMPT = (
    "Phân tích hình ảnh này. Trả VỀ DUY NHẤT một đối tượng JSON hợp lệ "
    "(không markdown, không chú thích) với các khoá:\n"
    '{"caption": "<mô tả ngắn gọn nội dung chính>", '
    '"ocr_text": "<toàn bộ chữ hiển thị trên ảnh, rỗng nếu không có>", '
    '"objects": ["<vật thể/chủ thể chính>", ...], '
    '"shot_type": "<closeup|medium|wide|product|text_only|other>", '
    '"quality": "<sharp|blurry|low_res>", '
    '"mood": "<tông màu/cảm xúc chung>"}'
)


def _client(api_key: str):
    from groq import Groq
    return Groq(api_key=api_key)


def _parse_json(text: str) -> dict:
    """Bóc JSON ra khỏi câu trả lời (phòng model thêm markdown fence)."""
    text = (text or "").strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"caption": text[:200], "ocr_text": "", "objects": [],
                "shot_type": "other", "quality": "unknown", "mood": ""}


def analyze_images(image_paths: list[str | Path], api_key: str | list[str],
                   extra_prompt: str = "") -> list[dict]:
    """Quét 1-3 ảnh trong 1 request, trả list kết quả JSON theo đúng thứ tự.

    api_key có thể là 1 key (str) hoặc list key (xoay vòng + fallback).
    """
    if not image_paths:
        return []
    image_paths = image_paths[:3]  # hard limit của qwen3.8-27b
    keys = [api_key] if isinstance(api_key, str) else list(api_key)

    prompt = ANALYZE_PROMPT + (("\nLưu ý thêm: " + extra_prompt) if extra_prompt else "")

    def call(key):
        from groq import Groq
        client = Groq(api_key=key)
        content: list[dict] = []
        for p in image_paths:
            content.append({"type": "image_url",
                            "image_url": {"url": image_to_data_url(p)}})
        content.append({"type": "text", "text": prompt})
        resp = client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_completion_tokens=900,  # free tier OTPM = 1000
        )
        return resp.choices[0].message.content or ""

    if len(keys) > 1:
        pool = _get_pool(keys)
        raw, _ = retry_with_pool(pool, call)
    else:
        raw = call(keys[0])

    # JSON mode trả 1 object; nếu nhiều ảnh cần tách. Ở đây mỗi ảnh = 1 lần
    # gọi đơn để model không nhập nhằng, nên 1 ảnh -> 1 kết quả.
    return [_parse_json(raw)] if len(image_paths) == 1 else [_parse_json(raw)]


def analyze_image(path: str | Path, api_key: str,
                  extra_prompt: str = "") -> dict:
    """Tiện ích 1 ảnh -> 1 dict."""
    res = analyze_images([path], api_key, extra_prompt=extra_prompt)
    return res[0] if res else {}


def describe_asset(path: str | Path, api_key: str) -> dict:
    """Mô tả 1 asset (ảnh hoặc video). Video -> cắt 3 keyframe -> gộp mô tả."""
    p = Path(path)
    if p.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv", ".avi"):
        from .clip import extract_keyframes
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            frames = extract_keyframes(p, td, n=3)
            descs = []
            for f in frames:
                d = analyze_image(f, api_key)
                descs.append(d)
            # gộp caption + ocr + objects
            return {
                "caption": " | ".join(d.get("caption", "") for d in descs if d.get("caption")),
                "ocr_text": " ".join(d.get("ocr_text", "") for d in descs if d.get("ocr_text")),
                "objects": sorted({o for d in descs for o in d.get("objects", [])}),
                "shot_types": [d.get("shot_type", "") for d in descs],
                "quality": "sharp" if any(d.get("quality") == "sharp" for d in descs)
                           else (descs[-1].get("quality", "unknown") if descs else "unknown"),
            }
    return analyze_image(p, api_key)


def match_scene(scene: dict, asset_descriptions: dict[str, dict],
                api_key: str, model_text: Optional[str] = None) -> Optional[str]:
    """Chọn asset_id phù hợp nhất cho scene dựa trên visual_intent.

    Dùng chính Groq để so sánh ngữ nghĩa intent vs mô tả asset (không cần
    embedding riêng). Trả asset_id hoặc None nếu không asset nào khớp đủ.
    """
    intent = scene.get("visual_intent", "")
    if not intent or not asset_descriptions:
        return None
    # đóng gói danh sách ứng viên thành text ngắn
    cand_lines = []
    for aid, d in asset_descriptions.items():
        blob = " ".join(filter(None, [
            d.get("caption", ""), d.get("ocr_text", ""),
            " ".join(d.get("objects", [])),
        ]))[:200]
        cand_lines.append(f"- id:{aid} :: {blob}")
    if not cand_lines:
        return None

    prompt = (
        f"Mục tiêu hình ảnh của cảnh: \"{intent}\"\n"
        "Dưới đây là danh sách tài nguyên có sẵn (id :: mô tả).\n"
        + "\n".join(cand_lines) +
        "\nChọn DUY NHẤT id tài nguyên phù hợp nhất về nội dung với mục tiêu. "
        "Nếu không có cái nào thực sự phù hợp, trả về null. "
        "Trả về JSON: {\"asset_id\": \"<id>\", \"reason\": \"<1 câu>\"}"
    )
    try:
        client = _client(api_key)
        resp = client.chat.completions.create(
            model=model_text or GROQ_VISION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_completion_tokens=500,  # free tier OTPM = 1000
        )
        out = _parse_json(resp.choices[0].message.content or "")
        aid = out.get("asset_id")
        if aid and aid in asset_descriptions:
            return str(aid)
    except Exception:
        return None
    return None
