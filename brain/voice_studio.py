"""Gemini Flash reference voice settings and non-destructive local audio processing."""
import base64
import io
import json
import math
import subprocess
import hashlib
import wave
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .local_audio import ffmpeg_binary
from .keypool import KeyPool, retry_with_pool

MODEL = 'gemini-3.8-flash-tts'
LANGUAGES = {'Tiếng Việt': 'Vietnamese', 'English (US)': 'American English',
             'English (UK)': 'British English', '中文 · Trung': 'Mandarin Chinese',
             '日本語 · Nhật': 'Japanese', '한국어 · Hàn': 'Korean',
             'Français · Pháp': 'French', 'Deutsch · Đức': 'German'}
ACCENTS = {'Tự nhiên': '', 'Việt · miền Bắc': 'Northern Vietnamese accent',
           'Việt · miền Trung': 'Central Vietnamese accent', 'Việt · miền Nam': 'Southern Vietnamese accent'}
PERSONAS = {
    'Tự nhiên': ('Aoede', 'natural conversational delivery'),
    'Nam trầm · thuyết minh': ('Charon', 'low, warm, measured documentary narration'),
    'Nam trẻ · năng động': ('Puck', 'youthful, lively, confident delivery'),
    'Nữ sáng · năng động': ('Kore', 'bright, energetic, articulate delivery'),
    'Nữ ấm · kể chuyện': ('Aoede', 'warm, gentle storytelling'),
    'Trailer · mạnh mẽ': ('Fenrir', 'powerful, dramatic trailer delivery'),
}
TONES = {'Trung tính': 'neutral', 'Vui vẻ': 'cheerful', 'Bình tĩnh': 'calm',
         'Nghiêm túc': 'serious', 'Hào hứng': 'excited', 'Thì thầm': 'whispered', 'Kể chuyện': 'expressive storytelling'}
DEFAULT_PROCESSING = dict(speed=1.0, pitch=0.0, bass=0.0, treble=0.0, reverb=0.0, volume=100.0)
RANGES = dict(speed=(.5, 2), pitch=(-5, 5), bass=(-12, 12), treble=(-12, 12), reverb=(0, 50), volume=(0, 150))
_POOLS = {}


def validate_processing(settings):
    result = {}
    for key, default in DEFAULT_PROCESSING.items():
        value = float(settings.get(key, default))
        lo, hi = RANGES[key]
        if not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'Thông số {key} cần nằm trong {lo}–{hi}.')
        result[key] = value
    return result


def speech_style(settings):
    language = settings.get('language', 'Tiếng Việt')
    persona = settings.get('persona', 'Tự nhiên')
    tone = settings.get('tone', 'Trung tính')
    parts = [f'Speak in {LANGUAGES[language]}.', PERSONAS[persona][1], TONES[tone]]
    accent = ACCENTS.get(settings.get('accent', 'Tự nhiên'), '')
    if language == 'Tiếng Việt' and accent:
        parts.append(accent)
    if settings.get('direction', '').strip():
        parts.append(settings['direction'].strip()[:600])
    return '; '.join(parts)


def speech_payload(text, settings):
    if not text.strip() or len(text) > 1500:
        raise ValueError('Đoạn mẫu cần 1–1500 ký tự.')
    voice = settings.get('voice', 'Aoede')
    if voice not in ('Aoede', 'Kore', 'Puck', 'Charon', 'Fenrir'):
        raise ValueError('Giọng chưa hỗ trợ.')
    return {'model': MODEL, 'input': [{'type': 'user_input', 'content': [
        {'type': 'text', 'text': text, 'annotations': [{'type': 'speech_metadata', 'style': speech_style(settings)}]}]}],
        'response_format': {'type': 'audio'}, 'generation_config': {'speech_config': [{'voice': voice}]}}


def generate_sample(text, output, api_key, settings, opener=urlopen):
    """One explicit request; style metadata is never concatenated into spoken text."""
    body = json.dumps(speech_payload(text, settings), ensure_ascii=False).encode('utf-8')
    request = Request('https://generativelanguage.googleapis.com/v1beta/interactions', data=body,
                      headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key}, method='POST')
    try:
        with opener(request, timeout=90) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'Gemini HTTP {exc.code}. Kiểm tra quyền model, key hoặc quota.') from None
    except (URLError, TimeoutError):
        raise RuntimeError('Không kết nối được Gemini; chưa tự thử lại.') from None
    chunks = [c for step in result.get('steps', []) if step.get('type') == 'model_output'
              for c in step.get('content', []) if c.get('type') == 'audio' and c.get('data')]
    if not chunks:
        raise ValueError('Gemini không trả audio WAV.')
    data = base64.b64decode(chunks[-1]['data'], validate=True)
    with wave.open(io.BytesIO(data)) as audio:
        if audio.getnframes() <= 0:
            raise ValueError('Audio rỗng.')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return output


def _pool_for(keys):
    """Cache cooldown state without using a key value as the dictionary label."""
    clean = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
    if not clean:
        raise ValueError('Chưa có Gemini API key.')
    signature = hashlib.sha256('\0'.join(clean).encode('utf-8')).hexdigest()
    if signature not in _POOLS:
        _POOLS[signature] = KeyPool(clean, cooldown_seconds=120, max_consecutive_failures=1, base_delay=.25)
    return _POOLS[signature]


def generate_sample_with_keys(text, output, keys, settings, generator=generate_sample):
    """Use all configured keys round-robin; never return or persist the selected key."""
    pool = _pool_for(keys)
    result, _used_key = retry_with_pool(
        pool, lambda key: generator(text, output, key, settings), max_rounds=len(pool))
    return result, pool.available_count, len(pool)


def audio_duration(path):
    with wave.open(str(path)) as audio:
        return audio.getnframes() / audio.getframerate()


def filter_chain(settings):
    s = validate_processing(settings)
    factor = 2 ** (s['pitch'] / 12)
    filters = ['aresample=24000', f'asetrate={24000 * factor:.6f}', 'aresample=24000']
    tempo = s['speed'] / factor
    while tempo < .5:
        filters.append('atempo=0.5'); tempo /= .5
    while tempo > 2:
        filters.append('atempo=2'); tempo /= 2
    filters += [f'atempo={tempo:.8f}', f"bass=g={s['bass']}:f=110", f"treble=g={s['treble']}:f=4500"]
    if s['reverb']:
        # Short room-like echo, intentionally modest; not a convolution room model.
        filters.append(f"aecho=0.8:0.9:55:{s['reverb']/250:.4f}")
    filters += [f"volume={s['volume']/100:.5f}", 'alimiter=limit=0.95:level=false']
    return ','.join(filters)


def process_sample(source, destination, settings):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Cần file mới để bảo toàn bản gốc.')
    chain = filter_chain(settings)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg_binary(), '-v', 'error', '-nostdin', '-i', str(source), '-vn', '-af', chain,
                    '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(destination)],
                   check=True, capture_output=True, timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return destination, audio_duration(destination)
