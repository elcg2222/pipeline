"""Trích keyframe từ video/ảnh bằng ffmpeg cho vision scanning.

Groq qwen3.8-27b chỉ nhận tối đa 3 ảnh/request và không nhận video, nên
video được cắt thành keyframe trước rồi mới gửi đi quét.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_keyframes(video_path: str | Path, out_dir: str | Path,
                      n: int = 3, max_width: int = 1280) -> list[Path]:
    """Cắt n khung hình cách đều từ video, resize tối đa max_width để gửi API gọn.

    Trả về danh sách đường dẫn ảnh jpg đã sinh.
    """
    video = Path(video_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not ffmpeg_available():
        raise RuntimeError("thiếu ffmpeg; cài: winget install Gyan.FFmpeg")

    # lấy tổng thời lượng để đặt mốc đều
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        duration = 0.0
    if duration <= 0:
        # fallback: 1 khung tại giây 0
        points = [0.0]
    else:
        # tránh khung đen đầu/cuối
        lo, hi = duration * 0.08, duration * 0.92
        if n == 1:
            points = [(lo + hi) / 2]
        else:
            points = [lo + (hi - lo) * i / (n - 1) for i in range(n)]

    files: list[Path] = []
    for i, t in enumerate(points):
        dest = out / f"{video.stem}_kf{i + 1}.jpg"
        args = [
            "ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", f"scale='min({max_width},iw)':-2",
            "-q:v", "3", str(dest),
        ]
        subprocess.run(args, capture_output=True)
        if dest.exists() and dest.stat().st_size > 0:
            files.append(dest)
    return files


def image_to_data_url(path: str | Path) -> str:
    """Đọc ảnh -> data URL base64 cho Groq vision."""
    import base64
    import mimetypes
    p = Path(path)
    mime = mimetypes.guess_type(str(p))[0] or "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"
