import base64
import io
import json
import math
import struct
import wave
from unittest.mock import patch
import pytest
from brain.voice_studio import speech_payload, generate_sample, generate_sample_with_keys, process_sample, audio_duration, validate_processing, filter_chain, MODEL


def signal(path, seconds=1.0):
    values = [int(10000 * math.sin(2 * math.pi * 440 * i / 24000)) for i in range(int(24000 * seconds))]
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(struct.pack('<' + 'h' * len(values), *values))
    return path


def pitch(path):
    with wave.open(str(path)) as audio:
        data = audio.readframes(audio.getnframes())
        values = struct.unpack('<' + 'h' * (len(data)//2), data)
        return sum(a <= 0 < b for a, b in zip(values, values[1:])) / (len(values)/audio.getframerate())


def test_language_and_style_separate_from_transcript():
    settings = dict(language='Tiếng Việt', accent='Việt · miền Nam', persona='Nam trầm · thuyết minh', tone='Bình tĩnh', voice='Charon', direction='Pause naturally')
    payload = speech_payload('Xin chào Việt Nam.', settings)
    assert payload['model'] == 'gemini-3.8-flash-tts'
    part = payload['input'][0]['content'][0]
    assert part['text'] == 'Xin chào Việt Nam.'
    assert 'Southern Vietnamese' in part['annotations'][0]['style']
    settings['language'] = 'English (US)'
    assert 'Vietnamese accent' not in speech_payload('Hello.', settings)['input'][0]['content'][0]['annotations'][0]['style']


def test_response_wav_and_request_contract(tmp_path):
    original = signal(tmp_path / 'original.wav')
    response = dict(steps=[dict(type='model_output', content=[dict(type='audio', data=base64.b64encode(original.read_bytes()).decode())])])
    def opener(request, timeout):
        assert timeout == 90
        assert json.loads(request.data)['model'] == MODEL
        assert 'SECRET' not in request.full_url
        return io.BytesIO(json.dumps(response).encode())
    out = generate_sample('Hello.', tmp_path / 'output.wav', 'SECRET', {}, opener=opener)
    assert out.read_bytes() == original.read_bytes()


def test_multiple_keys_rotate_without_persisting_key(tmp_path, monkeypatch):
    import brain.voice_studio as studio
    studio._POOLS.clear()
    used = []
    def generator(text, output, key, settings):
        used.append(key)
        if key == 'bad':
            raise RuntimeError('429 quota')
        return signal(output)
    monkeypatch.setattr('brain.keypool.time.sleep', lambda _seconds: None)
    output, available, total = generate_sample_with_keys('Test', tmp_path / 'voice.wav', ['bad', 'good'], {}, generator)
    assert used == ['bad', 'good']
    assert output.is_file() and available == 1 and total == 2
    assert 'bad' not in str(output) and 'good' not in str(output)


def test_processing_changes_speed_preserves_pitch_and_original(tmp_path):
    original = signal(tmp_path / 'dry.wav', 2)
    before = original.read_bytes()
    fast, duration = process_sample(original, tmp_path / 'fast.wav', {'speed': 2})
    assert .9 < duration < 1.1
    assert 425 < pitch(fast) < 455
    high, duration = process_sample(original, tmp_path / 'high.wav', {'pitch': 5})
    assert 1.9 < duration < 2.1
    assert 570 < pitch(high) < 605
    assert original.read_bytes() == before
    with pytest.raises(ValueError):
        process_sample(original, original, {})


def test_processing_limits_and_mute(tmp_path):
    with pytest.raises(ValueError):
        validate_processing({'pitch': float('nan')})
    with pytest.raises(ValueError):
        validate_processing({'speed': 4})
    source = signal(tmp_path / 'dry.wav')
    out, _ = process_sample(source, tmp_path / 'mute.wav', {'volume': 0, 'bass': 12, 'treble': -12, 'reverb': 50})
    with wave.open(str(out)) as audio:
        assert not any(audio.readframes(audio.getnframes()))
    assert 'atempo=2' in filter_chain({'speed': 2, 'pitch': -5})


def test_studio_history_preset_and_scene_recipe(tmp_path):
    import tkinter as tk
    from desktop_app import PreviewWindow, _apply_style
    from brain.project import create_project
    from brain.scenes import Scene
    from brain.profile import save_profile
    project = create_project({}, '', '', [Scene('a', narration='Mẫu')], [], tmp_path, 'studio')
    root = tk.Tk(); root.withdraw(); _apply_style(root)
    pane = PreviewWindow(root, str(project))
    try:
        pane.voice_language.set('English (US)')
        pane.voice_tone.set('Vui vẻ')
        pane.voice_processing['speed'].set(1.25)
        settings = pane.studio_settings()
        pane.save_voice_preset(); pane.voice_language.set('Tiếng Việt'); pane.load_voice_preset()
        assert pane.voice_language.get() == 'English (US)'
        source = signal(tmp_path / 'test.wav')
        pane.receive_studio_sample(dict(dry=(source, 1), wet=(source, 1), recipe=settings))
        pane.voice_processing['speed'].set(2)  # Unapplied changes must not be attributed to this audio.
        pane.attach_audio_sample()
        profile = save_profile(project, pane.scenes)
        assert profile['scenes'][0]['voice_recipe']['processing']['speed'] == 1.25
        assert profile['scenes'][0]['voice_recipe']['language'] == 'English (US)'
        pane.select_studio_sample()
        assert pane.voice_processing['speed'].get() == 1.25
    finally:
        pane._on_close(); root.destroy()
