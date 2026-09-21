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
    stem = f"{row['native_id'] or row['uid'].split(':')[-1]}_{safe_name(row['title'], 40)}"
    return d / f"{stem}.mp4"


def _via_direct(url: str, referer: str, dest: Path, timeout: int) -> bool:
    if not url:
        return False
    tmp = dest.with_suffix(".part")
    code, _, err = run_cmd([
        "yt-dlp", url, "-o", str(tmp), "--no-part", "--quiet", "--no-warnings",
        "--user-agent", UA, "--referer", referer,
    ], timeout=timeout)
    if code == 0 and tmp.exists() and tmp.stat().st_size > 50_000:
        tmp.replace(dest)
        return True
    tmp.unlink(missing_ok=True)
    return False


def _via_ytdlp(url: str, dest: Path, cfg: dict, timeout: int) -> bool:
    tmp = dest.with_suffix(".part")
    args = [
        "yt-dlp", url, "-o", str(tmp), "--no-part", "--quiet", "--no-warnings",
        "-f", cfg.get("ytdlp_format", "bv*[height<=1080]+ba/b[height<=1080]/b"),
        "--merge-output-format", "mp4", "--user-agent", UA,
        "--retries", "3", "--socket-timeout", "20",
    ]
    ck = cfg.get("cookies_file")
    if ck and Path(ck).exists():
        args += ["--cookies", ck]
    elif cfg.get("cookies_from_browser"):
        args += ["--cookies-from-browser", cfg["cookies_from_browser"]]
    if cfg.get("proxy"):
        args += ["--proxy", cfg["proxy"]]

    code, _, err = run_cmd(args, timeout=timeout)
    if code == 0 and tmp.exists() and tmp.stat().st_size > 50_000:
        tmp.replace(dest)
        return True
    log.debug("yt-dlp fail %s: %s", url, err[:200])
    tmp.unlink(missing_ok=True)
    return False


def _via_f2(url: str, dest: Path, cfg: dict, timeout: int) -> bool:
    """f2 CLI: f2 dy -c conf.yaml -u <url>. Cần file config f2 riêng."""
    conf = cfg.get("f2_config")
    if not conf or not Path(conf).exists() or not which("f2"):
        return False
    outdir = dest.parent / "_f2tmp"
    outdir.mkdir(exist_ok=True)
    code, _, err = run_cmd(["f2", "dy", "-c", conf, "-u", url, "-p", str(outdir)],
                           timeout=timeout)
    if code != 0:
        log.debug("f2 fail: %s", err[:200])
        shutil.rmtree(outdir, ignore_errors=True)
        return False
    vids = sorted(outdir.rglob("*.mp4"), key=lambda p: p.stat().st_size, reverse=True)
    if not vids:
        shutil.rmtree(outdir, ignore_errors=True)
        return False
    shutil.move(str(vids[0]), str(dest))
    shutil.rmtree(outdir, ignore_errors=True)
    return True


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
        got = (_via_direct(row["play_url"] or "", referer, dest, timeout)
               or _via_ytdlp(url, dest, dl, timeout)
               or _via_f2(url, dest, dl, timeout))

        if got:
            store.set_state(uid, "downloaded", local_path=str(dest))
            log.info("OK  %-9s %s (%.1f MB)", row["platform"], dest.name,
                     dest.stat().st_size / 1e6)
            ok += 1
        else:
            store.bump_attempt(uid, "tất cả downloader đều thất bại")
            store.set_state(uid, "queued")          # trả về hàng đợi để lần sau thử lại
            log.warning("FAIL %s", url)
            fail += 1
        time.sleep(dl.get("delay_seconds", 2))

    store.log_run("download", "", started, ok, fail)
    return {"ok": ok, "fail": fail}
