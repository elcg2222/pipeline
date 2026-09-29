import json
import zipfile
from pathlib import Path

from brain.assembly import (parse_script, scan_library, suggest_assets,
                            assemble_project, export_package, resolve_aspect_ratio)
from brain.scenes import load_scenes
from brain.handoff import patch_project_for_flow3


def test_chapter_split_does_not_mix_previous_narration():
    scenes = parse_script("# A\n## Mèo\nMèo chơi.\n# B\n## Chó\nChó ngủ.")
    assert len(scenes) == 2
    assert scenes[0]["chapter_id"] == "A"
    assert scenes[0]["narration"] == "Mèo chơi."
    assert scenes[1]["chapter_id"] == "B"
    assert len(parse_script("Đoạn một.\n\nĐoạn hai.")) == 2


def test_catalog_mapping_matching_and_zip(tmp_path):
    library = tmp_path / "downloads" / "meme"
    library.mkdir(parents=True)
    media = library / "meo_vui.png"
    media.write_bytes(b"fixture media")
    (library / "manifest.jsonl").write_text(json.dumps({"local_path":"downloads/meme/meo_vui.png", "title":"Mèo vui", "commercial_use": True, "source_url":"https://example.test/cat"}), encoding="utf-8")
    catalog = scan_library(library, tmp_path)
    assert catalog[0]["title"] == "Mèo vui"
    assert not catalog[0]["license_review_required"]
    scenes = suggest_assets(parse_script("## Mèo vui\nMột chú mèo."), catalog)
    assert scenes[0]["asset_ids"] == [catalog[0]["asset_id"]]
    assert scenes[0]["match_method"] == "metadata_keywords"
    project = assemble_project("script", scenes, catalog, tmp_path / "outputs", "Test")
    brief = json.loads((project / "brief.json").read_text(encoding="utf-8"))
    assert brief["aspect_ratio"] == "16:9"  # invalid fixture cannot be measured; no 9:16 fallback
    assert brief["aspect_ratio_source"].startswith("auto_fallback")
    assert (project / "PROJECT_ROADMAP.md").is_file()
    assert load_scenes(project / "scenes.json")[0].needs_visual_review
    (project / "config.yaml").write_text("SECRET=do-not-export", encoding="utf-8")
    output = export_package(project, tmp_path / "handoff.zip")
    with zipfile.ZipFile(output) as archive:
        assert "preview_profile.json" in archive.namelist()
        assert "PROJECT_ROADMAP.md" in archive.namelist()
        assert any(n.startswith("media/") for n in archive.namelist())
        assert "config.yaml" not in archive.namelist()
        assert not any(n.startswith("revisions/") for n in archive.namelist())


def test_no_match_keeps_scene_empty_and_manual_match_is_preserved():
    assets = [{"asset_id":"a", "title":"Ocean", "description":{}}]
    scenes = parse_script("## Mèo\nChú mèo đang chơi")
    assert not suggest_assets(scenes, assets)[0]["asset_ids"]
    scenes[0]["asset_ids"] = ["manual"]
    assert suggest_assets(scenes, assets)[0]["asset_ids"] == ["manual"]


def test_ambiguous_legacy_cache_is_not_used(tmp_path):
    for sub in ("one", "two"):
        folder = tmp_path / sub; folder.mkdir()
        (folder / "clip.jpg").write_bytes(b"image")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "asset_descriptions.json").write_text('{"clip":{"caption":"unreliable"}}', encoding="utf-8")
    rows = scan_library(tmp_path, tmp_path)
    assert len({a["asset_id"] for a in rows}) == 2
    assert all(not a["caption"] for a in rows)


def test_auto_aspect_uses_first_selected_real_asset(tmp_path):
    from PIL import Image
    landscape = tmp_path / "youtube.png"
    portrait = tmp_path / "short.png"
    Image.new("RGB", (1600, 900), "blue").save(landscape)
    Image.new("RGB", (900, 1600), "red").save(portrait)
    catalog = [{"asset_id": "wide", "source_file": str(landscape)},
               {"asset_id": "tall", "source_file": str(portrait)}]
    assert resolve_aspect_ratio("auto", [{"asset_ids": ["wide"]}], catalog)[0] == "16:9"
    assert resolve_aspect_ratio("auto", [{"asset_ids": ["tall"]}], catalog)[0] == "9:16"
    assert resolve_aspect_ratio("1:1", [], [])[0] == "1:1"


def test_flow3_patch_inherits_project_ratio_instead_of_forcing_default(tmp_path):
    project = assemble_project("script", parse_script("## Cảnh\nLời."), [],
                               tmp_path, "Vertical", "9:16")
    patch_project_for_flow3(project)
    scenes = json.loads((project / "scenes.json").read_text(encoding="utf-8"))
    assert scenes[0]["format"] == "9:16"
    profile = json.loads((project / "preview_profile.json").read_text(encoding="utf-8"))
    assert profile["aspect_ratio"] == "9:16"
