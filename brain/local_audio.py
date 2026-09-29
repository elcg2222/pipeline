"""Optional local audio device playback; no Windows paths or notebook syntax.

Headless Colab can use decode_audio without opening an audio device.
Install desktop playback: python -m pip install pygame-ce imageio-ffmpeg
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


def ffmpeg_binary():
    found = shutil.which("ffmpeg")
    if found:
        return found
    if importlib.util.find_spec("imageio_ffmpeg") is not None:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    raise RuntimeError("Cài ffmpeg hoặc python -m pip install imageio-ffmpeg")


def decode_audio(source, destination):
    """Decode to seekable OGG at 44.1k stereo, also usable on Colab/Linux."""
    result = subprocess.run([ffmpeg_binary(), "-v", "error", "-y", "-i", str(source),
        "-vn", "-map", "0:a:0", "-ac", "2", "-ar", "44100", "-c:a", "libvorbis", str(destination)],
        capture_output=True, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-400:])


def prepare_audio(source, cache):
    path, cache = Path(source).resolve(), Path(cache)
    sig = f"{path}:{path.stat().st_mtime_ns}:{path.stat().st_size}"
    cached = cache / (hashlib.sha256(sig.encode("utf-8")).hexdigest()[:24] + ".ogg")
    cache.mkdir(parents=True, exist_ok=True)
    if not cached.exists():
        temporary = cache / (uuid.uuid4().hex + ".ogg")
        try:
            decode_audio(path, temporary)
            if not cached.exists():
                temporary.replace(cached)
        finally:
            temporary.unlink(missing_ok=True)
    return cached


class LocalAudio:
    def __init__(self, cache):
        self.cache = Path(cache)
        self._generation = 0
        self._lock = threading.Lock()
        self._mixer = None
        self.error = ""
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="preview-audio")
        self._future = None

    def stop(self):
        with self._lock:
            self._generation += 1
            if self._future:
                self._future.cancel()
            if self._mixer:
                self._mixer.music.stop()
                self._mixer.music.unload()

    def play(self, source, offset=0.0, duration=None):
        self.stop()
        generation = self._generation
        self.error = ""
        started = time.monotonic()
        def worker():
            try:
                if importlib.util.find_spec("pygame") is None:
                    raise RuntimeError("Cài âm thanh local: python -m pip install pygame-ce")
                cached = prepare_audio(source, self.cache)
                os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
                import pygame.mixer as mixer
                with self._lock:
                    if generation != self._generation:
                        return
                    elapsed = time.monotonic() - started
                    if duration is not None and elapsed >= duration:
                        return
                    if not mixer.get_init():
                        mixer.init(frequency=44100, size=-16, channels=2)
                    self._mixer = mixer
                    mixer.music.load(str(cached))
                    mixer.music.play(start=max(0.0, offset + elapsed))
            except Exception as exc:
                if generation == self._generation:
                    self.error = f"Audio mẫu: {exc}"
        self._future = self._executor.submit(worker)

    def close(self):
        self.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
