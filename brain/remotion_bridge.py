"""Project-local Remotion launcher, usable from Windows or Colab/Linux."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

from .profile import save_profile, stage_remotion, write_json
from .preview import load_project

STUDIO = Path(__file__).resolve().parents[1] / "preview_studio"
_process = None
_render_lock = threading.Lock()


def render_preview(project_dir, cancel=None):
    """Blocking worker API: local low-res MP4, no Studio/browser and no paid APIs."""
    cancel = cancel or threading.Event()
    if not _render_lock.acquire(blocking=False):
        raise RuntimeError("Đang dựng một preview khác. Hãy chờ hoặc hủy tác vụ đó.")
    try:
        node = shutil.which("node")
        cli = STUDIO / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
        if not node or not cli.is_file():
            raise RuntimeError("Thiếu Remotion: chạy npm ci trong preview_studio.")
        root = Path(project_dir).resolve()
        profile = stage_remotion(root, STUDIO, update_active=False)
        profile['soft_subtitles'] = True
        cache = root / ".preview_cache"
        cache.mkdir(exist_ok=True)
        token = uuid.uuid4().hex[:12]
        props = cache / f"props_{token}.json"
        output = cache / f"preview_r{profile['revision']}_{token}.mp4"
        write_json(props, {"profile": profile})
        active = STUDIO / "src" / "active-profile.json"
        if not active.exists():
            shutil.copy2(STUDIO / "src" / "sample-profile.json", active)
        if cancel.is_set():
            raise RuntimeError("Đã hủy dựng preview.")
        log = cache / f"render_{token}.log"
        with log.open("w", encoding="utf-8") as stream:
            proc = subprocess.Popen([node, str(cli), "render", "src/index.tsx", "Preview", str(output),
                "--props", str(props), "--scale=0.5", "--concurrency=2"], cwd=STUDIO,
                stdout=stream, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                while True:
                    if cancel.is_set():
                        proc.terminate()
                        raise RuntimeError("Đã hủy dựng preview.")
                    try:
                        code = proc.wait(timeout=0.2)
                        break
                    except subprocess.TimeoutExpired:
                        continue
            finally:
                if proc.poll() is None:
                    proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait()
        if code != 0 or not output.is_file():
            detail = log.read_text(encoding="utf-8", errors="replace")[-1800:]
            raise RuntimeError(f"Remotion chưa dựng được. Log: {log}\n{detail}")
        if any(scene.get("audio") for scene in profile["scenes"]):
            from .local_audio import prepare_audio
            prepare_audio(output, cache / "audio")
        if cancel.is_set():
            raise RuntimeError("Đã hủy dựng preview.")
        return output
    finally:
        _render_lock.release()


def open_studio(project_dir):
    global _process
    node = shutil.which("node")
    cli = STUDIO / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    if not node or not cli.exists():
        raise RuntimeError("Cần Node.js và chạy npm install trong preview_studio trước.")
    stage_remotion(project_dir, STUDIO)
    if _process is None or _process.poll() is not None:
        log = STUDIO / "studio.log"
        with log.open("a", encoding="utf-8") as stream:
            _process = subprocess.Popen([node, str(STUDIO / "studio.cjs")],
                                        cwd=STUDIO, stdout=stream, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return _process


def stop_studio():
    """Stop only the Studio process launched by this desktop process."""
    global _process
    if _process is not None and _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
    _process = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--stage-only", action="store_true")
    args = parser.parse_args()
    save_profile(args.project, load_project(args.project)["scenes"])
    if args.stage_only:
        stage_remotion(args.project, STUDIO)
    else:
        open_studio(args.project).wait()
