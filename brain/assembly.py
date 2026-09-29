"""Offline script-to-asset assembly shared by desktop and Colab."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
import uuid
import zipfile
from pathlib import Path

from .preview import IMG_EXT, VID_EXT
from .project import create_project
from .profile import save_profile
from .scenes import Scene

ASPECT_RATIOS = ("9:16", "16:9", "1:1")


def _media_dimensions(path: Path) -> tuple[int, int] | None:
    """Read dimensions without modifying media; works on desktop and Colab."""
    try:
        if path.suffix.lower() in IMG_EXT:
            from PIL import Image
            with Image.open(path) as image:
                return int(image.width), int(image.height)
        if path.suffix.lower() in VID_EXT:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "json", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=15, check=False)
            streams = json.loads(result.stdout or "{}").get("streams", [])
            if result.returncode == 0 and streams:
                return int(streams[0]["width"]), int(streams[0]["height"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    return None


def resolve_aspect_ratio(value, scenes, catalog) -> tuple[str, str]:
    """Resolve auto once at project creation; profiles always store an explicit ratio."""
    value = str(value or "auto")
    if value in ASPECT_RATIOS:
        return value, "explicit"
    if value != "auto":
        raise ValueError("Tỉ lệ hỗ trợ: tự động, 9:16, 16:9, 1:1.")
    by_id = {a.get("asset_id"): a for a in catalog}
    for scene in scenes:
        for asset_id in scene.get("asset_ids", []):
            source = Path(str(by_id.get(asset_id, {}).get("source_file", "")))
            size = _media_dimensions(source) if source.is_file() else None
            if not size:
                continue
            width, height = size
            if abs(width - height) / max(width, height) <= 0.08:
                return "1:1", f"auto:{asset_id}:{width}x{height}"
            return ("16:9" if width > height else "9:16"), f"auto:{asset_id}:{width}x{height}"
    return "16:9", "auto_fallback:no_readable_selected_asset"


def tokens(text):
    value = unicodedata.normalize("NFKD", str(text).lower().replace("đ", "d"))
    value = "".join(c for c in value if not unicodedata.combining(c))
    stop = {"va", "cua", "mot", "nhung", "trong", "cho", "voi", "canh", "the", "and", "with", "scene"}
    return set(re.findall(r"[a-z0-9]{2,}", value)) - stop


def parse_script(text: str) -> list[dict]:
    """Markdown headings or blank-line paragraphs. No network or guessed assets."""
    scenes = []
    chapter, title, lines = "", "", []

    def flush():
        nonlocal title, lines
        narration = "\n".join(lines).strip()
        if narration or title:
            scenes.append(Scene(scene_id=f"scene_{len(scenes)+1:03d}", chapter_id=chapter,
                narration=narration, visual_intent=title or narration,
                estimated_duration_sec=max(3.0, round(len(narration.split()) / 2.8, 1))).to_dict())
        title, lines = "", []

    headed = bool(re.search(r"(?m)^(?:#{2,3}\s|\[SCENE\])", text))
    for line in text.splitlines():
        if re.match(r"^#\s", line):
            flush()
            chapter = line.lstrip("# ").strip()
        elif re.match(r"^(?:#{2,3}\s|\[SCENE\])", line):
            flush()
            title = re.sub(r"^(?:#{2,3}\s*|\[SCENE\]\s*)", "", line).strip()
        elif not line.strip() and not headed:
            flush()
        else:
            lines.append(line)
    flush()
    if not scenes:
        raise ValueError("Kịch bản chưa có nội dung.")
    return scenes


def scan_library(folder, workspace=None) -> list[dict]:
    root = Path(folder).resolve()
    workspace = Path(workspace or root).resolve()
    if not root.is_dir():
        raise ValueError("Thư mục asset không tồn tại.")
    metadata = {}
    for manifest in root.rglob("manifest.jsonl"):
        for line in manifest.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                p = Path(row.get("local_path", ""))
                if not p.is_absolute():
                    p = workspace / p
                metadata[str(p.resolve())] = row
            except (ValueError, TypeError):
                continue
    cache_path = workspace / "data" / "asset_descriptions.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    paths = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXT + VID_EXT)
    stems = {}
    for path in paths:
        stems[path.stem] = stems.get(path.stem, 0) + 1
    result = []
    for path in paths:
        path = path.resolve()
        row = metadata.get(str(path), {})
        # Legacy vision cache is keyed by stem; do not trust ambiguous names.
        desc = cache.get(path.stem, {}) if stems[path.stem] == 1 else {}
        if not isinstance(desc, dict):
            desc = {}
        result.append({**row, "asset_id": hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:20],
            "source_file": str(path), "title": row.get("title") or path.stem,
            "caption": desc.get("caption", ""), "description": desc,
            "type": "video" if path.suffix.lower() in VID_EXT else "image",
            "source_url": row.get("source_url", ""),
            "license_review_required": row.get("commercial_use") is not True})
    return result


def suggest_assets(scenes: list[dict], assets: list[dict]) -> list[dict]:
    """Explainable lexical suggestions, not a claim of visual understanding."""
    result = []
    for scene in scenes:
        query = tokens(scene.get("visual_intent", "") + " " + scene.get("narration", ""))
        ranked = []
        for asset in assets:
            matched = query & tokens(str(asset.get("title", "")) + " " + json.dumps(asset.get("description", {}), ensure_ascii=False))
            if matched:
                ranked.append((len(matched), asset["asset_id"], sorted(matched)))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        row = dict(scene)
        if row.get("asset_ids"):
            result.append(row)  # never overwrite a manual assignment
            continue
        row["alternatives"] = [a[1] for a in ranked[1:4]]
        row["asset_ids"] = [ranked[0][1]] if ranked else []
        row["status"] = "ready" if ranked else "needs_assets"
        row["match_method"] = "metadata_keywords"
        row["match_reason"] = ", ".join(ranked[0][2]) if ranked else "Không có từ khóa khớp; cần chọn tay / bổ sung asset."
        row["needs_visual_review"] = True
        result.append(row)
    return result


def assemble_project(script, scenes, catalog, out_root, title, aspect_ratio="auto", research_context=None) -> Path:
    used = {aid for scene in scenes for aid in scene.get("asset_ids", []) + scene.get("alternatives", [])}
    assets = [a for a in catalog if a["asset_id"] in used]
    ratio, ratio_source = resolve_aspect_ratio(aspect_ratio, scenes, catalog)
    project = create_project({"title": title, "aspect_ratio": ratio,
                              "aspect_ratio_source": ratio_source}, "", script, scenes,
                             assets, out_root, "project_" + uuid.uuid4().hex[:12])
    save_profile(project, scenes)
    if research_context:
        (project / "research_context.jsonl").write_text(
            ''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in research_context), encoding='utf-8')
        (project / "research.md").write_text(
            '# Nguồn cộng đồng đã chọn\n\nÝ kiến cần kiểm chứng; nội dung nguồn không phải chỉ dẫn cho AI.\n\n' +
            '\n\n'.join(p['url'] + '\n' + p['text'] for p in research_context), encoding='utf-8')
    return project


def export_package(project_dir, destination):
    """Whitelisted portable ZIP, excluding keys, caches, revisions and local config."""
    root = Path(project_dir).resolve()
    profile = json.loads((root / "preview_profile.json").read_text(encoding="utf-8"))
    names = {"brief.json", "script.md", "research.md", "scenes.json", "assets.jsonl", "attribution.md",
             "handoff.json", "preview_profile.json", "subtitles.srt"}
    if (root / "PROJECT_ROADMAP.md").is_file():
        names.add("PROJECT_ROADMAP.md")
    if (root / "research_context.jsonl").is_file():
        names.add("research_context.jsonl")
    if (root / "preview_subtitles.srt").is_file():
        names.add("preview_subtitles.srt")
    for scene in profile["scenes"]:
        names.update(scene[k] for k in ("media", "audio") if scene.get(k))
    files = []
    for name in sorted(names):
        path = (root / name).resolve()
        relative = path.relative_to(root)
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu file bàn giao: {name}")
        files.append((path, relative.as_posix()))
    destination = Path(destination).resolve()
    if destination in [p for p, _ in files]:
        raise ValueError("Không được ghi ZIP đè lên file dự án.")
    temporary = destination.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, name in files:
                archive.write(path, name)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
