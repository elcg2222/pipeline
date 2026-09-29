"""Manual local integration test: real FFmpeg + Remotion + embedded Tk playback.

Run from repository: python -B -m tests.integrated_preview_smoke
Uses generated test media and silence, never remote APIs or credentials.
Keeps a demo project under outputs/ so it can be opened from the desktop app.
"""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from brain.assembly import assemble_project, export_package, parse_script, scan_library, suggest_assets
from brain.local_audio import LocalAudio, decode_audio, ffmpeg_binary
from brain.remotion_bridge import render_preview
from brain.profile import save_profile


def main():
    os.environ["SDL_AUDIODRIVER"] = "dummy"  # exercise decode/playback without making sound
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        video = folder / "kiem_tra_video.mp4"
        image = folder / "kiem_tra_anh.png"
        audio = folder / "sample.wav"
        common = [ffmpeg_binary(), "-y", "-v", "error"]
        subprocess.run(common + ["-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30", "-t", "2", "-c:v", "libx264", str(video)], check=True)
        subprocess.run(common + ["-i", str(video), "-frames:v", "1", str(image)], check=True)
        subprocess.run(common + ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(audio)], check=True)
        script = "## Kiểm tra ảnh\nẢnh và chữ trong app.\n## Kiểm tra video\nVideo và hiệu ứng chạy local."
        catalog = scan_library(folder, root)
        scenes = suggest_assets(parse_script(script), catalog)
        scenes[0]["asset_ids"] = [a["asset_id"] for a in catalog if a["type"] == "image"]
        scenes[1]["asset_ids"] = [a["asset_id"] for a in catalog if a["type"] == "video"]
        for index, scene in enumerate(scenes):
            scene["estimated_duration_sec"] = 2
            scene["on_screen_text"] = "Một app · Hai mục" if index == 0 else "Kịch bản → Preview"
            scene["text_effect"] = "pop" if index == 0 else "slide"
        project = assemble_project(script, scenes, catalog, root / "outputs", "Kiểm tra preview trong app")
        for scene in scenes:
            (project / "audio" / (scene["scene_id"] + ".wav")).write_bytes(audio.read_bytes())
        save_profile(project, scenes)
    movie = render_preview(project)
    import imageio.v2 as imageio
    reader = imageio.get_reader(str(movie))
    metadata = reader.get_meta_data()
    assert abs(metadata["duration"] - 4) < .1
    assert reader.get_data(80).size > 0
    reader.close()
    decoded = project / ".preview_cache" / "audio-check.ogg"
    decode_audio(movie, decoded)
    player = LocalAudio(project / ".preview_cache" / "audio")
    player.play(movie, offset=.2, duration=4)
    deadline = time.monotonic() + 15
    while player._future and not player._future.done() and time.monotonic() < deadline:
        time.sleep(.05)
    assert not player.error, player.error
    assert player._mixer is not None
    player.close()
    import tkinter as tk
    from desktop_app import PreviewWindow
    window = tk.Tk(); window.withdraw()
    host = tk.Frame(window); host.pack()
    preview = PreviewWindow(host, str(project), embedded=True)
    preview._rendered_path = str(movie)
    preview._show_scene(1, offset=.5)
    assert preview._vid_frame == 75
    assert preview._vid_reader is not None
    preview._on_close(); window.destroy()
    package = export_package(project, project.parent / (project.name + ".zip"))
    print(json.dumps({"project":str(project), "preview":str(movie), "package":str(package),
                      "duration": metadata["duration"], "embedded_video_and_local_audio":"passed"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
