"""Tải video gốc.

Chiến lược 3 lớp cho mỗi item:
  1. play_url  - nếu provider đã trả link CDN không watermark -> tải thẳng (nhanh nhất)
  2. yt-dlp    - hỗ trợ tốt TikTok/YouTube, và Douyin ở mức chấp nhận được
  3. f2 / dtk  - fallback chuyên biệt cho Douyin khi yt-dlp bó tay

Mọi file tải dở lưu đuôi .part rồi mới rename -> không bao giờ để lại file hỏng
khiến stage QC hiểu nhầm là đã tải xong.
"""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from core.store import Store
from core.util import run_cmd, safe_name, which

log = logging.getLogger("stage.download")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def _target(cfg: dict, row) -> Path:
    base = Path(cfg.get("download_dir", "downloads"))
    d = base / safe_name(row["topic"] or "misc", 40) / row["platform"]
    d.mkdir(parents=True, exist_ok=True)
    raw_title = row["title"] if "title" in row.keys() else ""
    stem = f"{row['native_id'] or row['uid'].split(':')[-1]}_{safe_name(raw_title or '', 40)}"
    return d / f"{stem}.mp4"


def _part_template(dest: Path) -> Path:
    """Template có extension rõ ràng để yt-dlp merge về `*.part.mp4`."""
    return dest.with_name(f"{dest.stem}.part.%(ext)s")


def _cleanup_partial(dest: Path):
    """Dọn riêng file tạm của đúng video, kể cả video/audio fragment của yt-dlp."""
    for p in dest.parent.glob(f"{dest.stem}.part*"):
        if p.is_file():
            p.unlink(missing_ok=True)


def _finish_partial(dest: Path) -> bool:
    """Chỉ chấp nhận file mp4 đã merge; không nhầm fragment webm là thành phẩm."""
    candidates = [p for p in dest.parent.glob(f"{dest.stem}.part.mp4")
                  if p.is_file() and p.stat().st_size > 50_000]
    if not candidates:
        return False
    max(candidates, key=lambda p: p.stat().st_size).replace(dest)
    _cleanup_partial(dest)
    return True


def _via_direct(url: str, referer: str, dest: Path, timeout: int) -> tuple[bool, str]:
    if not url:
        return False, "không có play_url trực tiếp"
    _cleanup_partial(dest)
    code, _, err = run_cmd([
        "yt-dlp", url, "-o", str(_part_template(dest)), "--no-part", "--quiet", "--no-warnings",
        "--user-agent", UA, "--referer", referer,
    ], timeout=timeout)
    if code == 0 and _finish_partial(dest):
        return True, ""
    _cleanup_partial(dest)
    return False, (err or "tải play_url thất bại")[:500]


def _via_ytdlp(url: str, dest: Path, cfg: dict, timeout: int) -> tuple[bool, str]:
    _cleanup_partial(dest)
    # Không có ffmpeg thì không thể ghép video/audio rời. Ưu tiên một file MP4
    # hoàn chỉnh (thường 360p/720p) thay vì tải xong fragment rồi báo thất bại.
    has_ffmpeg = bool(which("ffmpeg"))
    if not has_ffmpeg:
        return False, "thiếu ffmpeg: cần để ghép audio/video và chạy QC. Cài: winget install Gyan.FFmpeg"
    video_format = cfg.get("ytdlp_format", "bv*[height<=1080]+ba/b[height<=1080]")
    args = [
        "yt-dlp", url, "-o", str(_part_template(dest)), "--no-part", "--quiet", "--no-warnings",
        "-f", video_format, "--user-agent", UA,
        "--retries", "3", "--socket-timeout", "20", "--http-chunk-size", "0",
    ]
    args += ["--merge-output-format", "mp4"]
    ck = cfg.get("cookies_file")
    if ck and Path(ck).exists():
        args += ["--cookies", ck]
    elif cfg.get("cookies_from_browser"):
        args += ["--cookies-from-browser", cfg["cookies_from_browser"]]
    if cfg.get("proxy"):
        args += ["--proxy", cfg["proxy"]]

    code, _, err = run_cmd(args, timeout=timeout)
    if code != 0:
        # Retry mà không có cookies-from-browser vì có thể bị khóa file cookie trong Chrome
        args_no_ck = [a for a in args if a not in ("--cookies-from-browser", cfg.get("cookies_from_browser", ""))]
        code, _, err = run_cmd(args_no_ck, timeout=timeout)

    if code == 0 and _finish_partial(dest):
        return True, ""
    log.debug("yt-dlp fail %s: %s", url, err[:200])
    _cleanup_partial(dest)
    return False, (err or "yt-dlp không tạo được file video")[:500]


def _via_f2(url: str, dest: Path, cfg: dict, timeout: int) -> tuple[bool, str]:
    """f2 CLI: f2 dy -c conf.yaml -u <url>. Cần file config f2 riêng."""
    conf = cfg.get("f2_config")
    if not conf or not Path(conf).exists() or not which("f2"):
        return False, "f2 chưa được cấu hình hoặc chưa cài"
    outdir = dest.parent / "_f2tmp"
    outdir.mkdir(exist_ok=True)
    code, _, err = run_cmd(["f2", "dy", "-c", conf, "-u", url, "-p", str(outdir)],
                           timeout=timeout)
    if code != 0:
        log.debug("f2 fail: %s", err[:200])
        shutil.rmtree(outdir, ignore_errors=True)
        return False, (err or "f2 tải thất bại")[:500]
    vids = sorted(outdir.rglob("*.mp4"), key=lambda p: p.stat().st_size, reverse=True)
    if not vids:
        shutil.rmtree(outdir, ignore_errors=True)
        return False, "f2 không tạo được file mp4"
    shutil.move(str(vids[0]), str(dest))
    shutil.rmtree(outdir, ignore_errors=True)
    return True, ""


def run(store: Store, cfg: dict, limit: int = 20) -> dict:
    started = time.time()
    dl = cfg.get("download", {})
    timeout = dl.get("timeout", 300)
    ok = fail = 0

    rows = store.pick("queued", limit=limit, max_attempts=dl.get("max_attempts", 3))
    if not rows:
        log.info("Không có video nào ở trạng thái 'queued'.")
        return {"ok": 0, "fail": 0}

    for row in rows:
        uid, url = row["uid"], row["url"]
        dest = _target(cfg, row)

        if dest.exists() and dest.stat().st_size > 50_000:
            store.set_state(uid, "downloaded", local_path=str(dest))
            ok += 1
            continue

        store.set_state(uid, "downloading")
        referer = f"https://www.{row['platform']}.com/"
        play_url = row["play_url"] if "play_url" in row.keys() else ""
        got, reason = _via_direct(play_url or "", referer, dest, timeout)
        if not got:
            got, reason = _via_ytdlp(url, dest, dl, timeout)
        if not got:
            got, fallback_reason = _via_f2(url, dest, dl, timeout)
            # Không để fallback chưa cấu hình che mất lỗi hữu ích của yt-dlp.
            if not got and fallback_reason != "f2 chưa được cấu hình hoặc chưa cài":
                reason = f"yt-dlp: {reason}; f2: {fallback_reason}"[:500]

        if got:
            store.set_state(uid, "downloaded", local_path=str(dest))
            log.info("OK  %-9s %s (%.1f MB)", row["platform"], dest.name,
                     dest.stat().st_size / 1e6)
            ok += 1
        else:
            store.bump_attempt(uid, reason)
            store.set_state(uid, "queued")          # trả về hàng đợi để lần sau thử lại
            log.warning("FAIL %s | %s", url, reason[:300])
            fail += 1
        time.sleep(dl.get("delay_seconds", 2))

    store.log_run("download", "", started, ok, fail)
    return {"ok": ok, "fail": fail}
