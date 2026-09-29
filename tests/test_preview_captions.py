import json
import wave
from pathlib import Path
from unittest.mock import patch
import pytest
from brain.preview_captions import parse_srt, active_cues, estimated_cues, load_captions
from brain.project import create_project
from brain.scenes import Scene

SRT = '1\n00:00:00,500 --> 00:00:01,000\nXin chào\n\n2\n00:00:01,000 --> 00:00:02,000\nTiếng Việt\n'

def test_exact_cue_boundaries_and_gaps():
    cues = parse_srt('\ufeff' + SRT.replace('\n', '\r\n'))
    assert not active_cues(cues, .499)
    assert active_cues(cues, .5)[0][1]['text'] == 'Xin chào'
    assert active_cues(cues, 1)[0][1]['text'] == 'Tiếng Việt'
    assert not active_cues(cues, 2)
    with pytest.raises(ValueError):
        parse_srt('1\n00:00:02,000 --> 00:00:01,000\nSai')

def test_estimate_reflows_but_custom_srt_stays_absolute(tmp_path):
    from brain.srt import scenes_to_srt
    scenes = [dict(scene_id='a', narration='một hai ba bốn năm sáu bảy tám chín mười mười một', estimated_duration_sec=4)]
    (tmp_path / 'scenes.json').write_text(json.dumps(scenes), encoding='utf-8')
    (tmp_path / 'subtitles.srt').write_text(scenes_to_srt(scenes), encoding='utf-8')
    tl = [dict(start=0, duration=8, subtitle=scenes[0]['narration'])]
    cues, mode = load_captions(tmp_path, tl)
    assert len(cues) == 2 and cues[-1]['end'] == 8 and 'ước tính' in mode
    (tmp_path / 'preview_subtitles.srt').write_text(SRT, encoding='utf-8')
    assert load_captions(tmp_path, tl)[0][-1]['end'] == 2

def test_overlay_seek_toggle_audio_and_profile(tmp_path):
    import tkinter as tk
    from desktop_app import PreviewWindow, _apply_style
    from brain.profile import save_profile
    from brain.preview import load_project
    from brain.assembly import export_package
    import zipfile
    project = create_project({'aspect_ratio': '9:16'}, '', '', [Scene('a', narration='Xin chào', estimated_duration_sec=3)], [], tmp_path, 'demo')
    (project / 'preview_subtitles.srt').write_text(SRT, encoding='utf-8')
    root = tk.Tk(); root.withdraw(); _apply_style(root)
    preview = PreviewWindow(root, str(project))
    try:
        root.update_idletasks()
        assert len(preview.inspector_tabs.tabs()) == 4
        preview._on_seek(.75)
        assert preview.canvas.find_withtag('preview_caption')
        assert preview._active_caption_ids == ('0',)
        preview._on_seek(1.5)
        assert preview._active_caption_ids == ('1',)
        preview._on_seek(2.1)
        assert not preview.canvas.find_withtag('preview_caption')
        preview._on_seek(.75)
        preview.caption_enabled.set(False); preview.update_caption_overlay()
        assert not preview.canvas.find_withtag('preview_caption')
        preview.caption_enabled.set(True); preview.update_caption_overlay()
        assert preview.canvas.find_withtag('preview_caption')
        audio = tmp_path / 'sample.wav'
        with wave.open(str(audio), 'wb') as w:
            w.setparams((1, 2, 24000, 0, 'NONE', 'not compressed')); w.writeframes(b'\0\0' * 48000)
        preview._tts_sample = (audio, 2.0)
        preview.attach_audio_sample()
        assert preview.timeline[0]['duration'] == 2
        profile = save_profile(project, preview.scenes)
        assert profile['audio_role'] == 'reference_only'
        assert profile['scenes'][0]['audio'].startswith('audio/reference_')
        assert Path(load_project(project)['audio']['a']).is_file()
        assert (project / 'preview_subtitles.srt').read_text(encoding='utf-8') == SRT
        with zipfile.ZipFile(export_package(project, tmp_path / 'sample.zip')) as z:
            assert 'preview_subtitles.srt' in z.namelist()
            assert profile['scenes'][0]['audio'] in z.namelist()
        preview._on_seek(2)
        assert preview.play_t == 2 and not preview.canvas.find_withtag('preview_caption')
    finally:
        preview._on_close(); root.destroy()
