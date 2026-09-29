import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain.profile import save_profile, stage_remotion
from brain.preview import load_project, build_timeline, inspect_visual_quality
from brain.project import create_project
from brain.scenes import Scene, load_scenes
from brain.srt import scenes_to_srt


class PreviewProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = create_project({"aspect_ratio":"9:16"}, "", "", [Scene("a")], [], self.root, "demo")

    def test_extensions_revisions_approval_and_silent_scene(self):
        scenes = [{"scene_id":"a", "estimated_duration_sec":2, "review_notes":"Giữ nhịp", "text_effect":"pop"},
                  {"scene_id":"b", "estimated_duration_sec":3, "narration":"Xin chào"}]
        profile = save_profile(self.project, scenes, approved=True)
        self.assertEqual(profile["audio_role"], "reference_only")
        self.assertTrue(profile["final_voiceover_required"])
        self.assertIn("00:00:02,000 --> 00:00:05,000", (self.project / "subtitles.srt").read_text(encoding="utf-8"))
        self.assertEqual(load_scenes(self.project / "scenes.json")[0].review_notes, "Giữ nhịp")
        self.assertEqual(save_profile(self.project, scenes)["revision"], 2)
        self.assertEqual(len(list((self.project / "revisions").iterdir())), 2)
        self.assertEqual(json.loads((self.project / "preview_profile.json").read_text(encoding="utf-8"))["review_status"], "draft")

    def test_video_is_not_a_keyframe_and_wav_is_discovered(self):
        video = self.project / "media" / "clip.mp4"
        video.write_bytes(b"fake test media")
        (self.project / "audio" / "a.wav").write_bytes(b"test")
        (self.project / "assets.jsonl").write_text(json.dumps({"asset_id":"clip", "media_file":"clip.mp4"}), encoding="utf-8")
        scenes = [{"scene_id":"a", "estimated_duration_sec":1, "asset_ids":["clip"]}]
        profile = save_profile(self.project, scenes)
        timeline = build_timeline(load_project(self.project))
        self.assertEqual(Path(timeline[0]["media"]).suffix, ".mp4")
        self.assertEqual(Path(timeline[0]["audio"]).suffix, ".wav")
        self.assertEqual(profile["scenes"][0]["media"], "media/clip.mp4")
        staged = stage_remotion(self.project, self.root / "studio")
        self.assertTrue((self.root / "studio" / "public" / staged["scenes"][0]["media"]).is_file())

    def test_invalid_duration_does_not_overwrite(self):
        before = (self.project / "scenes.json").read_bytes()
        with self.assertRaises(ValueError):
            save_profile(self.project, [{"scene_id":"a", "estimated_duration_sec":float("nan")}])
        self.assertEqual(before, (self.project / "scenes.json").read_bytes())

    def test_no_keys_production_creates_draft_without_tts(self):
        from brain.produce import run_production
        with patch("brain.produce.models.load_groq_keys", return_value=[]), patch("brain.produce.models.load_gemini_keys", return_value=[]):
            result = run_production({}, "", "", [Scene("a")], [], {}, self.root, "no_keys")
        self.assertEqual(result["audio"], 0)
        self.assertTrue((Path(result["project"]) / "preview_profile.json").exists())

    def test_near_solid_asset_is_visible_but_blocks_handoff_ready_status(self):
        from PIL import Image
        image = self.project / "media" / "green.png"
        Image.new("RGB", (1080, 1920), "#17652d").save(image)
        (self.project / "assets.jsonl").write_text(
            json.dumps({"asset_id": "green", "media_file": "green.png"}), encoding="utf-8")
        scenes = [{"scene_id": "a", "estimated_duration_sec": 1,
                   "asset_ids": ["green"], "status": "ready"}]
        profile = save_profile(self.project, scenes, approved=True)
        timeline = build_timeline(load_project(self.project))
        self.assertTrue(inspect_visual_quality(image)["warnings"])
        self.assertTrue(timeline[0]["visual_warnings"])
        self.assertIn("a", profile["asset_quality_warnings"])
        handoff = json.loads((self.project / "handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["status"], "needs_asset_review")


if __name__ == "__main__":
    unittest.main()
