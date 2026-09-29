"""Versioned asset/cue contract. Standard library only; no model or UI imports."""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath

SCHEMA = "studio.handoff.v1"
ROLES = {
    "main_video": ("video", {".mp4", ".mov", ".mkv", ".webm"}),
    "still": ("image", {".png", ".jpg", ".jpeg", ".webp"}),
    "overlay_image": ("image", {".png", ".jpg", ".jpeg", ".webp"}),
    "overlay_video": ("video", {".mp4", ".mov", ".mkv", ".webm"}),
    **{role: ("audio", {".wav", ".mp3", ".m4a", ".ogg", ".flac"}) for role in
       ("preview_narration", "voice_reference", "final_narration", "music", "sfx")},
    "font": ("font", {".ttf", ".otf"}),
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def contained(root, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Asset path must be relative POSIX")
    part = PurePosixPath(name)
    if part.is_absolute() or ".." in part.parts:
        raise ValueError("Asset path escapes project")
    path = (Path(root) / name).resolve()
    path.relative_to(Path(root).resolve())
    return path


def number(value, minimum=0, positive=False):
    value = float(value)
    if not math.isfinite(value) or value < minimum or (positive and value == 0):
        raise ValueError("Invalid finite time/rate")
    return value


def register(root, project, source, role, *, description="", source_url="", license="unreviewed"):
    """Copy user-selected media into this project; never alter the original."""
    if role not in ROLES:
        raise ValueError("Unsupported asset role")
    source = Path(source).resolve()
    kind, extensions = ROLES[role]
    if source.suffix.lower() not in extensions or not source.is_file():
        raise ValueError("File extension does not match role")
    sha = digest(source)
    asset_id = "asset_" + sha
    for asset in project["assets"]:
        if asset["asset_id"] == asset_id:
            if role not in asset["roles"]:
                asset["roles"].append(role)
            return asset_id
    name = "resources/" + kind + "/" + sha + source.suffix.lower()
    target = contained(root, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and digest(target) != sha:
        raise ValueError("Existing content-addressed resource is corrupt")
    if not target.exists():
        shutil.copyfile(source, target)
    project["assets"].append({"asset_id": asset_id, "kind": kind, "roles": [role],
        "path": name, "sha256": sha, "size_bytes": target.stat().st_size,
        "description": str(description), "source_url": str(source_url), "license": str(license)})
    return asset_id


def from_preview(root):
    """Explicit import; existing handoff resources/cues are preserved by scene ID."""
    root = Path(root)
    profile = read(root / "preview_profile.json")
    old = read(root / "studio.project.json") if (root / "studio.project.json").exists() else {}
    if old and old.get("schema") != SCHEMA:
        raise ValueError("Unsupported existing handoff schema")
    project = {"schema": SCHEMA, "project_id": profile["project_id"],
        "producer": "local_pipeline", "revision": profile.get("revision", 1),
        "aspect_ratio": profile.get("aspect_ratio", "9:16"), "fps": profile.get("fps", 30),
        "timing_source": "estimated", "assets": old.get("assets", []),
        "cues": old.get("cues", []), "effects_required": old.get("effects_required", []), "scenes": []}
    previous = {s["scene_id"]: s for s in old.get("scenes", [])}
    for scene in profile["scenes"]:
        sid = scene["scene_id"]
        media = scene.get("media")
        if not media:
            raise ValueError(f"Missing media: {sid}")
        source = contained(root, media)
        role = "still" if source.suffix.lower() in ROLES["still"][1] else "main_video"
        aid = register(root, project, source, role)
        row = {"scene_id": sid, "asset_id": aid, "narration": scene.get("narration", ""),
            "on_screen_text": scene.get("on_screen_text", ""),
            "text_effect": scene.get("text_effect", "fade"),
            "duration_s": number(scene.get("estimated_duration_sec", 5), positive=True),
            "trim_in_s": number(scene.get("trim_in", 0)),
            "playback_rate": number(scene.get("playback_rate", 1), positive=True),
            "notes": scene.get("review_notes", "")}
        if scene.get("audio"):
            row["preview_audio_id"] = register(root, project, contained(root, scene["audio"]), "preview_narration")
        # A voice from a different transcript must be explicitly reassigned.
        prior = previous.get(sid, {})
        if prior.get("narration") == row["narration"] and prior.get("final_audio_id"):
            row["final_audio_id"] = prior["final_audio_id"]
        project["scenes"].append(row)
    validate(root, project)
    write(root / "studio.project.json", project)
    return project


def add_cue(project, asset_id, role, scene_id, *, offset_s=0, duration_s=1, gain_db=-12, loop=False):
    if role not in ("music", "sfx", "overlay_image", "overlay_video"):
        raise ValueError("Role does not use timeline cues")
    cue = {"cue_id": "cue_" + uuid.uuid4().hex, "asset_id": asset_id, "role": role,
        "scene_id": scene_id, "anchor": "scene_start", "offset_s": number(offset_s),
        "duration_s": number(duration_s, positive=True), "gain_db": float(gain_db), "loop": bool(loop)}
    project["cues"].append(cue)
    return cue


def validate(root, project):
    if project.get("schema") != SCHEMA:
        raise ValueError("Unsupported handoff schema")
    if project.get("aspect_ratio") not in ("9:16", "16:9", "1:1"):
        raise ValueError("Unsupported canvas ratio")
    number(project.get("fps", 30), positive=True)
    assets = {}
    for a in project["assets"]:
        if a["asset_id"] in assets or not a.get("roles"):
            raise ValueError("Duplicate asset ID or empty roles")
        p = contained(root, a["path"])
        for role in a["roles"]:
            if role not in ROLES or a["kind"] != ROLES[role][0] or p.suffix.lower() not in ROLES[role][1]:
                raise ValueError("Invalid asset kind/role")
        if not p.is_file() or digest(p) != a["sha256"] or p.stat().st_size != a["size_bytes"]:
            raise ValueError("Missing or modified resource: " + a["asset_id"])
        assets[a["asset_id"]] = a
    def ref(aid, role):
        if aid not in assets or role not in assets[aid]["roles"]:
            raise ValueError("Unknown asset or wrong role: " + str(aid))
    scenes = {}
    for s in project["scenes"]:
        sid = s["scene_id"]
        if sid in scenes or not re.fullmatch(r"[A-Za-z0-9_-]+", sid):
            raise ValueError("Invalid/duplicate scene ID")
        number(s["duration_s"], positive=True)
        number(s.get("trim_in_s", 0))
        number(s.get("playback_rate", 1), positive=True)
        if s["asset_id"] not in assets or not {"main_video", "still"} & set(assets[s["asset_id"]]["roles"]):
            raise ValueError("Missing scene visual")
        for field, role in (("preview_audio_id", "preview_narration"), ("final_audio_id", "final_narration")):
            if s.get(field):
                ref(s[field], role)
        scenes[sid] = s
    if not scenes:
        raise ValueError("Project has no scenes")
    seen = set()
    for c in project["cues"]:
        if c["cue_id"] in seen or c["scene_id"] not in scenes:
            raise ValueError("Duplicate cue or deleted scene reference")
        seen.add(c["cue_id"])
        if c["role"] not in ("music", "sfx", "overlay_image", "overlay_video"):
            raise ValueError("Unsupported cue role")
        ref(c["asset_id"], c["role"])
        if c.get("anchor") != "scene_start":
            raise ValueError("Unsupported anchor (scene_start supported in v1)")
        number(c["offset_s"])
        number(c["duration_s"], positive=True)
        gain = float(c.get("gain_db", -12))
        if not math.isfinite(gain) or not -60 <= gain <= 6:
            raise ValueError("Gain outside -60..6 dB")
    missing = [s["scene_id"] for s in scenes.values() if s.get("narration") and not s.get("final_audio_id")]
    return {"package_ready": True, "render_ready": False, "missing_final_voice": missing,
        "timing_source": "estimated", "media_probe_required": True,
        "effects_pending_capability_check": project.get("effects_required", [])}


def export_bundle(root, destination):
    """Standalone ZIP. No implicit upload; no legacy exporter behavior change."""
    root, destination = Path(root).resolve(), Path(destination).resolve()
    project = read(root / "studio.project.json")
    report = validate(root, project)
    # Whitelist contract fields; never serialize arbitrary source profile/key settings.
    top = ("schema", "project_id", "producer", "revision", "aspect_ratio", "fps", "timing_source", "effects_required")
    clean = {k: project[k] for k in top if k in project}
    fields = {
        "assets": ("asset_id", "kind", "roles", "path", "sha256", "size_bytes", "description", "source_url", "license"),
        "scenes": ("scene_id", "asset_id", "narration", "on_screen_text", "text_effect", "duration_s", "trim_in_s", "playback_rate", "notes", "preview_audio_id", "final_audio_id"),
        "cues": ("cue_id", "asset_id", "role", "scene_id", "anchor", "offset_s", "duration_s", "gain_db", "loop"),
    }
    for group, keys in fields.items():
        clean[group] = [{k: row[k] for k in keys if k in row} for row in project[group]]
        if any(set(row) - set(keys) for row in project[group]):
            raise ValueError(f"Unknown {group} fields: refusing to silently drop instructions")
    sources = {a["path"]: contained(root, a["path"]) for a in clean["assets"]}
    if destination == root / "studio.project.json" or destination in sources.values():
        raise ValueError("Cannot overwrite project source")
    if destination.exists():
        raise FileExistsError("Choose a new bundle revision; destination exists")
    temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("studio.project.json", json.dumps(clean, ensure_ascii=False, allow_nan=False))
            archive.writestr("reports/preflight.json", json.dumps(report, ensure_ascii=False))
            for name, path in sources.items():
                archive.write(path, name)
            package = Path(__file__).parent
            for path in package.glob("*.py"):
                archive.write(path, "studio_bridge/" + path.name)
            archive.write(package / "README.md", "STUDIO_README.md")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return report
