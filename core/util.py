from __future__ import annotations

import json
import logging
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("pipeline")


def setup_logging(level: str = "INFO", logfile: str | None = None):
    fmt = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if logfile:
        Path(logfile).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))
    logging.basicConfig(level=getattr(logging, level.upper(), 20),
                        format=fmt, handlers=handlers, force=True)


def which(cmd: str) -> str | None:
    return shutil.which(cmd) or shutil.which(cmd + ".cmd") or shutil.which(cmd + ".exe")


def run_cmd(args: list[str], timeout: int = 180, cwd: str | None = None) -> tuple[int, str, str]:
    """Chạy CLI ngoài. Trên Windows, npm-installed binary là .cmd nên cần resolve."""
    exe = which(args[0])
    if exe:
        args = [exe] + args[1:]
    log.debug("RUN %s", " ".join(args))
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"


def run_json(args: list[str], timeout: int = 180) -> Any:
    """Chạy CLI có -f json. Tự bóc phần JSON nếu CLI in kèm log rác."""
    code, out, err = run_cmd(args, timeout=timeout)
    if code == 66:                      # OpenCLI: EMPTY RESULT
        return []
    if code != 0:
        raise RuntimeError(f"exit {code}: {(err or out)[:400]}")
    out = out.strip()
    if not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        for opener, closer in (("[", "]"), ("{", "}")):
            i, j = out.find(opener), out.rfind(closer)
            if i != -1 and j > i:
                try:
                    return json.loads(out[i: j + 1])
                except json.JSONDecodeError:
                    continue
        raise RuntimeError(f"không parse được JSON: {out[:300]}")


def retry(times: int = 3, base: float = 2.0, exceptions=(Exception,)):
    """Backoff mũ + jitter. Bắt buộc khi gọi Douyin/TikTok để tránh bị chặn IP."""
    def deco(fn: Callable):
        def wrapper(*a, **kw):
            last = None
            for i in range(times):
                try:
                    return fn(*a, **kw)
                except exceptions as e:
                    last = e
                    if i == times - 1:
                        break
                    delay = base ** i + random.uniform(0, 1.5)
                    log.warning("%s thất bại (%s), thử lại sau %.1fs", fn.__name__, e, delay)
                    time.sleep(delay)
            raise last  # type: ignore
        return wrapper
    return deco


def polite_sleep(lo: float = 1.0, hi: float = 3.0):
    time.sleep(random.uniform(lo, hi))


def safe_name(s: str, maxlen: int = 60) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    s = "".join("_" if c in bad else c for c in (s or "")).strip(" .")
    return (s[:maxlen] or "untitled")
