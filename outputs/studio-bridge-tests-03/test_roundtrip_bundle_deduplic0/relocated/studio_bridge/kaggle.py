"""Build Flow3 inputs in a writable directory; never mutate an attached dataset.

Final speech can be supplied by any producer (including an AI-video notebook).
This adapter does not generate speech or silently promote preview audio.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from .project import contained, digest, read, validate, write

CAPABILITIES = {
    "static": "supported", "fade": "supported", "typewriter": "supported",
    "overlay_image": "supported", "music": "supported", "sfx": "supported",
    "overlay_video": "pending_source_phase_test", "pop": "pending_visual_parity",
    "slide": "pending_visual_parity", "optical_motion_blur": "not_implemented",
    "ai_interpolation": "external_preprocessing_required", "neon_glow": "not_implemented",
    "word_alignment": "external_alignment_required", "ducking": "not_implemented",
}


def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        raise RuntimeError("Media command failed: " + result.stderr[-3000:])
    return result.stdout


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))


def duration(info):
    from .project import number
    return number(info.get("format", {}).get("duration", 0), positive=True)


def inspect(root, project):
    report = validate(root, project)
    required = set(project.get("effects_required", []))
    required.update(s.get("text_effect", "static") for s in project["scenes"])
    required.update(c["role"] for c in project["cues"])
    report["unsupported"] = {r: CAPABILITIES.get(r, "unknown") for r in sorted(required)
                             if CAPABILITIES.get(r) != "supported"}
    effects = {s.get("text_effect", "static") for s in project["scenes"]}
    if len(effects) > 1:
        report["unsupported"]["per_scene_subtitle_effect"] = "current_Flow3_style_is_global"
    if any(s.get("on_screen_text") and s["on_screen_text"] != s.get("narration") for s in project["scenes"]):
        report["unsupported"]["independent_title_track"] = "requires_separate_text_renderer"
    return report


def prepare(root, output, *, draft=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError("Output must be outside the input project (use /kaggle/working)")
    project = read(root / "studio.project.json")
    report = inspect(root, project)
    if report["unsupported"]:
        raise ValueError("Unsupported required effects: " + json.dumps(report["unsupported"], ensure_ascii=False))
    if not draft and report["missing_final_voice"]:
        raise ValueError("Provide final_audio_id before final preparation: " + ", ".join(report["missing_final_voice"]))
    assets = {a["asset_id"]: a for a in project["assets"]}
    paths = {aid: contained(root, a["path"]) for aid, a in assets.items()}
    # Probe everything used before starting a render. Manifest validation alone is not media QC.
    used = {s["asset_id"] for s in project["scenes"]} | {c["asset_id"] for c in project["cues"]}
    used.update(s["final_audio_id"] for s in project["scenes"] if s.get("final_audio_id"))
    info = {aid: probe(paths[aid]) for aid in used}
    for aid in used:
        wanted = {"image": "video", "video": "video", "audio": "audio"}[assets[aid]["kind"]]
        if not any(s.get("codec_type") == wanted for s in info[aid]["streams"]):
            raise ValueError("Asset does not contain its declared media kind: " + aid)
    width, height = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (720, 720)}[project["aspect_ratio"]]
    fps = float(project["fps"])
    scenes, cursor = [], 0.0
    for source in project["scenes"]:
        s = dict(source)
        length = float(s["duration_s"])
        if s.get("final_audio_id"):
            length = max(length, duration(info[s["final_audio_id"]]))
        # Every cut must land on a frame boundary, otherwise concatenation drifts
        # from the subtitle/audio timeline by up to one frame per scene.
        length = math.ceil(length * fps - 1e-9) / fps
        aid = s["asset_id"]
        if assets[aid]["kind"] == "video":
            available = (duration(info[aid]) - float(s.get("trim_in_s", 0))) / float(s.get("playback_rate", 1))
            if available + 0.001 < length:
                raise ValueError("Footage too short after voice reflow: " + s["scene_id"])
        s.update(start_s=cursor, duration_s=length)
        cursor += length
        scenes.append(s)
    by_scene = {s["scene_id"]: s for s in scenes}
    for cue in project["cues"]:
        scene = by_scene[cue["scene_id"]]
        if cue["offset_s"] >= scene["duration_s"]:
            raise ValueError("Cue begins beyond its scene: " + cue["cue_id"])
        if scene["start_s"] + cue["offset_s"] + cue["duration_s"] > cursor + 0.001:
            raise ValueError("Cue extends beyond final timeline: " + cue["cue_id"])
        if cue["role"] in ("music", "sfx") and not cue.get("loop") and duration(info[cue["asset_id"]]) + 0.001 < cue["duration_s"]:
            raise ValueError("Audio cue longer than source without loop: " + cue["cue_id"])
    output.mkdir(parents=True, exist_ok=False)
    write(output / "preflight.json", report)
    clips, audio, tracks = [], [], []
    for index, scene in enumerate(scenes):
        aid = scene["asset_id"]
        target = output / f"scene_{index:04d}.mp4"
        args = ["ffmpeg", "-v", "error", "-nostdin"]
        if assets[aid]["kind"] == "image":
            args += ["-loop", "1", "-i", paths[aid]]
        else:
            args += ["-ss", str(scene.get("trim_in_s", 0)), "-i", paths[aid]]
        vf = (f"setpts=(PTS-STARTPTS)/{scene.get('playback_rate', 1)},"
              f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}")
        run(args + ["-vf", vf, "-t", scene["duration_s"], "-an", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", target])
        clips.append(target)
        if scene.get("final_audio_id"):
            audio.append({"path": str(paths[scene["final_audio_id"]]), "start_s": scene["start_s"], "gain_db": 0, "loop": False})
    # Filenames below are generated ASCII names, never interpolated user paths.
    concat = output / "concat.txt"
    concat.write_text("".join(f"file '{p.name}'\n" for p in clips), encoding="utf-8")
    working = output / "working.mp4"
    run(["ffmpeg", "-v", "error", "-nostdin", "-f", "concat", "-safe", "1", "-i", concat, "-c", "copy", working])
    for index, cue in enumerate(project["cues"]):
        start = by_scene[cue["scene_id"]]["start_s"] + cue["offset_s"]
        if cue["role"] in ("music", "sfx"):
            target = output / f"cue_{index:04d}.wav"
            args = ["ffmpeg", "-v", "error", "-nostdin"]
            if cue.get("loop"):
                args += ["-stream_loop", "-1"]
            run(args + ["-i", paths[cue["asset_id"]], "-t", cue["duration_s"], "-ar", "44100", "-ac", "2", target])
            audio.append({"path": str(target), "start_s": start, "gain_db": cue["gain_db"], "loop": False})
        else:
            tracks.append({"id": cue["cue_id"], "kind": "image", "source": str(paths[cue["asset_id"]]),
                "z": index + 1, "visibility": {"start_pct": start / cursor * 100, "end_pct": (start + cue["duration_s"]) / cursor * 100},
                "keyframes": [{"t_pct": start / cursor * 100, "x_pct": 50, "y_pct": 50, "width_pct": 30, "scale": 1, "opacity": 1, "rotation": 0}]})
    write(output / "flow2_package.json", {"schema": "flow2.package.v2", "job_key": project["project_id"],
        "timeline_mode": "working_video", "preprocess_speed": 1.0, "duration_ms": round(cursor * 1000),
        "video_width": width, "video_height": height, "working_video": str(working),
        "final_lines": [{"id": i + 1, "start_ms": round(s["start_s"] * 1000),
            "end_ms": round((s["start_s"] + s["duration_s"]) * 1000), "text_target": s.get("narration", ""),
            "source_text": s.get("narration", ""), "speaker_id": "S1"} for i, s in enumerate(scenes) if s.get("narration")]})
    write(output / "flow3.project.json", {"schema": "flow3.project.v2", "project_id": project["project_id"],
        "canvas": {"width": width, "height": height, "aspect": project["aspect_ratio"], "fps": fps}, "tracks": tracks,
        "metadata": {"subtitle_style": {"effect": scenes[0].get("text_effect", "static"), "studio_audio": audio}}})
    receipt = {"status": "prepared_draft" if draft else "prepared_with_final_audio", "rendered": False,
        "word_timing": "not_aligned", "scenes": scenes, "duration_s": cursor,
        "input_sha256": digest(root / "studio.project.json"), "original_audio": "excluded",
        "warning": "Layout is draft: centered 30% overlays. Preview audio never used. Review before final approval."}
    receipt["build_files"] = {p.name: digest(p) for p in (working, output / "flow2_package.json", output / "flow3.project.json")}
    receipt["audio_files"] = {item["path"]: digest(item["path"]) for item in audio}
    write(output / "prepare.report.json", receipt)
    return receipt


def render_prepared(folder, engine, *, expected_sha256=None):
    """Explicitly invoke a user-selected engine; no install, TTS, or network setup."""
    folder, engine = Path(folder).resolve(), Path(engine).resolve()
    if not engine.is_file():
        raise FileNotFoundError("Flow3 entrypoint not found")
    engine_hash = digest(engine)
    if expected_sha256 and engine_hash.lower() != expected_sha256.lower():
        raise ValueError("Engine hash differs from pinned version")
    receipt = read(folder / "prepare.report.json")
    if receipt.get("status") not in ("prepared_draft", "prepared_with_final_audio"):
        raise ValueError("Not a prepared Studio build")
    for name, expected in receipt["build_files"].items():
        if digest(contained(folder, name)) != expected:
            raise ValueError("Prepared build changed; prepare a new revision")
    for name, expected in receipt["audio_files"].items():
        if digest(name) != expected:
            raise ValueError("Prepared audio changed; prepare a new revision")
    output = folder / "flow3_render"
    if output.exists():
        raise FileExistsError("Render output exists; use a new build revision")
    log = run([sys.executable, engine, folder, "--project", folder / "flow3.project.json",
        "--working-video", folder / "working.mp4", "--output-dir", output,
        "--renderer", "ffmpeg", "--tts-backend", "mock_silent", "--render", "--no-menu"])
    video = output / "flow3_final.mp4"
    details = probe(video)
    actual = duration(details)
    if abs(actual - receipt["duration_s"]) > max(0.15, receipt["duration_s"] * 0.01):
        raise ValueError("Rendered duration differs from prepared timeline")
    has_audio = any(s.get("codec_type") == "audio" for s in details["streams"])
    studio = read(folder / "flow3.project.json")["metadata"]["subtitle_style"]
    if studio.get("studio_audio") and not has_audio:
        raise ValueError("Rendered file is missing expected audio stream")
    result = {"status": "rendered_needs_review", "draft": receipt["status"] == "prepared_draft",
        "engine_sha256": engine_hash, "duration_s": actual, "streams": details["streams"],
        "video": str(video), "human_audio_visual_review_required": True}
    (folder / "flow3.render.log").write_text(log, encoding="utf-8")
    write(folder / "render.report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "prepare", "render"))
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--draft", action="store_true", help="Allow missing final narration; never use preview TTS")
    parser.add_argument("--engine", type=Path, help="Explicit Flow3 entrypoint for render")
    parser.add_argument("--engine-sha256", help="Optional pinned engine checksum")
    args = parser.parse_args()
    if args.command == "inspect":
        report = inspect(args.project, read(args.project / "studio.project.json"))
    elif args.command == "render":
        if not args.engine:
            parser.error("render requires --engine")
        report = render_prepared(args.project, args.engine, expected_sha256=args.engine_sha256)
    else:
        if not args.output:
            parser.error("prepare requires --output outside dataset")
        report = prepare(args.project, args.output, draft=args.draft)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
