"""Cổng chất lượng - stage QUAN TRỌNG NHẤT mà pipeline V1 đang thiếu.

Lý do: AutoDub chạy GPU trên Kaggle/Colab, quota có hạn. Mỗi video rác lọt qua
là mất 5-10 phút GPU. QC ở local gần như miễn phí nên phải chặn ở đây:

  1. Video hỏng / thiếu audio stream           -> loại
  2. Độ phân giải < ngưỡng, bitrate quá thấp    -> loại
  3. Không có tiếng người (chỉ nhạc nền)        -> loại, vì AutoDub không có gì để dịch
  4. Trùng nội dung với video đã xử lý (pHash)  -> loại, chống đăng lại cùng 1 clip
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path

from core.store import Store
from core.util import run_cmd, which

log = logging.getLogger("stage.qc")


def ffprobe(path: str) -> dict:
    code, out, _ = run_cmd(["ffprobe", "-v", "quiet", "-print_format", "json",
                            "-show_format", "-show_streams", path], timeout=60)
    if code != 0:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def video_phash(path: str, frames: int = 5) -> str:
    """pHash trung bình của N khung hình -> chữ ký nội dung, bền với re-encode."""
    try:
        from PIL import Image
        import imagehash
    except ImportError:
        log.debug("thiếu Pillow/imagehash, bỏ qua dedupe nội dung")
        return ""

    info = ffprobe(path)
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    if dur <= 0:
        return ""

    bits: list[int] = []
    tmp = Path(path).with_suffix(".qc.jpg")
    for i in range(1, frames + 1):
        ts = dur * i / (frames + 1)
        code, _, _ = run_cmd(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ts:.2f}",
                              "-i", path, "-frames:v", "1", "-vf", "scale=256:-1",
                              str(tmp)], timeout=60)
        if code != 0 or not tmp.exists():
            continue
        try:
            h = imagehash.phash(Image.open(tmp))
            bits.append(int(str(h), 16))
        except Exception:
            pass
        finally:
            tmp.unlink(missing_ok=True)

    if not bits:
        return ""
    # bit-wise majority vote giữa các khung
    out = 0
    n = len(bits)
    for b in range(64):
        votes = sum((x >> b) & 1 for x in bits)
        if votes * 2 > n:
            out |= 1 << b
    return f"{out:016x}"


def speech_ratio(path: str) -> float:
    """Tỷ lệ thời lượng có tiếng nói, dùng Silero VAD. -1 nếu chưa cài."""
    try:
        import torch
        model, utils = torch.hub.load("snakers4/silero-vad", "silero_vad",
                                      trust_repo=True, onnx=False)
        get_ts, _, read_audio, *_ = utils
    except Exception:
        return -1.0

    wav_path = Path(path).with_suffix(".qc.wav")
    code, _, _ = run_cmd(["ffmpeg", "-y", "-loglevel", "error", "-i", path,
                          "-ac", "1", "-ar", "16000", str(wav_path)], timeout=120)
    if code != 0:
        return -1.0
    try:
        wav = read_audio(str(wav_path), sampling_rate=16000)
        ts = get_ts(wav, model, sampling_rate=16000)
        total = sum(t["end"] - t["start"] for t in ts)
        return total / max(len(wav), 1)
    except Exception:
        return -1.0
    finally:
        wav_path.unlink(missing_ok=True)


def run(store: Store, cfg: dict, limit: int = 50) -> dict:
    started = time.time()
    q = cfg.get("qc", {})
    ok = dropped = dup = 0

    if not which("ffprobe"):
        log.error("Chưa có ffmpeg/ffprobe trong PATH. winget install Gyan.FFmpeg")
        return {}

    for row in store.pick("downloaded", limit=limit):
        uid, path = row["uid"], row["local_path"]
        if not path or not Path(path).exists():
            store.set_state(uid, "queued", local_path="")
            continue

        info = ffprobe(path)
        streams = info.get("streams", [])
        vs = next((s for s in streams if s.get("codec_type") == "video"), None)
        as_ = next((s for s in streams if s.get("codec_type") == "audio"), None)

        reason = None
        if not vs:
            reason = "không có video stream"
        elif not as_ and q.get("require_audio", True):
            reason = "không có audio stream"
        else:
            h = int(vs.get("height") or 0)
            dur = float(info.get("format", {}).get("duration", 0) or 0)
            if h < q.get("min_height", 540):
                reason = f"độ phân giải thấp ({h}p)"
            elif dur < q.get("min_duration", 8):
                reason = f"quá ngắn ({dur:.1f}s)"

        if reason:
            store.set_state(uid, "qc_failed", last_error=reason)
            log.info("QC loại %s: %s", Path(path).name, reason)
            dropped += 1
            continue

        # tiếng nói
        if q.get("check_speech", False):
            sr = speech_ratio(path)
            if 0 <= sr < q.get("min_speech_ratio", 0.15):
                store.set_state(uid, "qc_failed", last_error=f"ít tiếng nói ({sr:.0%})")
                dropped += 1
                continue

        # trùng nội dung
        ph = video_phash(path) if q.get("check_phash", True) else ""
        if ph:
            twin = store.find_phash_near(ph, q.get("phash_distance", 6))
            if twin and twin != uid:
                store.set_state(uid, "duplicate", phash=ph, last_error=f"trùng {twin}")
                log.info("Trùng nội dung với %s -> bỏ %s", twin, Path(path).name)
                dup += 1
                continue

        store.set_state(uid, "downloaded", phash=ph)
        store.conn.execute("UPDATE videos SET last_error='qc_passed' WHERE uid=?", (uid,))
        store.conn.commit()
        ok += 1

    store.log_run("qc", "", started, ok, dropped + dup, f"dup={dup}")
    log.info("QC: đạt %d, loại %d, trùng %d", ok, dropped, dup)
    return {"ok": ok, "dropped": dropped, "duplicate": dup}
