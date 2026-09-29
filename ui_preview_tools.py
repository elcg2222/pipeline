"""Caption inspector and reference audio tools for the local preview player."""
import json
import shutil
import threading
import uuid
import wave
from pathlib import Path
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from brain.preview_captions import load_captions, parse_srt, active_cues, timestamp
from ui_voice_controls import VoiceStudioControls

STUDIO_APP = 'https://ai-vietnamese-multi-voice-studio.ai.studio/'


class PreviewTools(VoiceStudioControls):
    def build_caption_tools(self, parent):
        self.caption_enabled = tk.BooleanVar(value=True)
        self.caption_source = tk.StringVar()
        self.caption_clock = tk.StringVar(value='')
        self._active_caption_ids = ()
        row = ttk.Frame(parent); row.pack(fill='x', pady=8)
        ttk.Checkbutton(row, text='Sub trên hình', variable=self.caption_enabled, command=self.update_caption_overlay).pack(side='left')
        ttk.Button(row, text='Nhập SRT', command=self.import_preview_srt).pack(side='right')
        ttk.Label(parent, textvariable=self.caption_source, wraplength=330).pack(fill='x')
        ttk.Label(parent, textvariable=self.caption_clock, wraplength=330, foreground='#4f8cff').pack(fill='x', pady=8)
        holder = ttk.Frame(parent); holder.pack(fill='both', expand=True)
        self.cue_tree = ttk.Treeview(holder, columns=('start', 'end', 'text'), show='headings', height=10, selectmode='browse')
        for name, label, width in [('start', 'Bắt đầu', 95), ('end', 'Kết thúc', 95), ('text', 'Nội dung', 160)]:
            self.cue_tree.heading(name, text=label); self.cue_tree.column(name, width=width)
        self.cue_tree.tag_configure('active', background='#254876', foreground='white')
        scroll = ttk.Scrollbar(holder, command=self.cue_tree.yview)
        self.cue_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y'); self.cue_tree.pack(fill='both', expand=True)
        self.cue_tree.bind('<Double-1>', self.seek_caption)
        ttk.Label(parent, text='Bấm đúp câu để nhảy tới thời điểm đó. Sub là lớp xem trước, không ghi lên video gốc.', wraplength=330).pack(fill='x', pady=8)
        self.reload_captions()

    def reload_captions(self):
        try:
            self.cues, source = load_captions(self.project_dir, self.timeline)
        except ValueError as exc:
            self.cues, source = [], 'SRT lỗi: ' + str(exc)
        self.caption_source.set(source)
        self.cue_tree.delete(*self.cue_tree.get_children())
        for i, cue in enumerate(self.cues):
            self.cue_tree.insert('', 'end', iid=str(i), values=(timestamp(cue['start']), timestamp(cue['end']), cue['text']))
        self._active_caption_ids = ()

    def import_preview_srt(self):
        name = filedialog.askopenfilename(filetypes=[('Phụ đề SRT', '*.srt')])
        if not name:
            return
        try:
            text = Path(name).read_text(encoding='utf-8-sig')
            if not parse_srt(text):
                raise ValueError('SRT không có câu nào.')
            target = self.project_dir / 'preview_subtitles.srt'
            if target.exists():
                backup = self.project_dir / 'revisions' / ('subtitles-' + uuid.uuid4().hex)
                backup.mkdir(parents=True)
                shutil.copy2(target, backup / target.name)
            target.write_text(text, encoding='utf-8')
            self.reload_captions(); self.update_caption_overlay()
        except Exception as exc:
            messagebox.showerror('Nhập SRT', str(exc))

    def seek_caption(self, event=None):
        selected = self.cue_tree.selection()
        if selected:
            self.pause()
            self._on_seek(self.cues[int(selected[0])]['start'])

    def update_caption_overlay(self):
        if not hasattr(self, 'cues'):
            return
        cur = self.timeline[self.play_idx]['start'] + self.play_t
        active = active_cues(self.cues, cur)
        ids = tuple(str(i) for i, _ in active)
        if ids != self._active_caption_ids:
            for item in self._active_caption_ids:
                if self.cue_tree.exists(item):
                    self.cue_tree.item(item, tags=())
            for item in ids:
                self.cue_tree.item(item, tags=('active',))
            if ids:
                self.cue_tree.see(ids[0])
            self._active_caption_ids = ids
        self.caption_clock.set(' · '.join(f"Câu {i+1}: {timestamp(c['start'])} → {timestamp(c['end'])}" for i, c in active) or 'Khoảng trống · không có phụ đề')
        cv = self.canvas
        cv.delete('preview_caption')
        if not active or not self.caption_enabled.get():
            return
        # Place inside actual displayed picture, accounting for portrait letterboxing.
        w, h = cv.winfo_width(), cv.winfo_height()
        pw = self._photo.width() if self._photo is not None else w
        ph = self._photo.height() if self._photo is not None else h
        width = max(30, int(pw * .86))
        x, y = w / 2, (h + ph) / 2 - max(14, ph * .08)
        content = '\n'.join(c['text'] for _, c in active)
        size = max(10, min(24, int(pw / 23)))
        item = cv.create_text(x, y, text=content, fill='white', anchor='s', justify='center',
                              width=width, font=('Segoe UI', size, 'bold'), tags='preview_caption')
        bounds = cv.bbox(item)
        while bounds and bounds[3] - bounds[1] > ph * .5 and size > 8:
            size -= 1; cv.itemconfigure(item, font=('Segoe UI', size, 'bold')); bounds = cv.bbox(item)
        if bounds:
            bg = cv.create_rectangle(bounds[0]-8, bounds[1]-5, bounds[2]+8, bounds[3]+5,
                                     fill='#111827', outline='', tags='preview_caption')
            cv.tag_lower(bg, item)

    def build_audio_tools(self, parent):
        import webbrowser
        from brain.models import GEMINI_TTS_MODEL
        self._tts_busy = False
        self._tts_sample = None
        self.tts_status = tk.StringVar(value='Tạo hoặc nhập một đoạn mẫu, nghe và gắn vào cảnh đang chọn.')
        self.tts_key_status = tk.StringVar(value='Đang kiểm tra Gemini key…')
        ttk.Label(parent, text='VOICE STUDIO', font=('Segoe UI', 16, 'bold'), foreground='#7fe7df').pack(anchor='w', pady=(8, 2))
        ttk.Label(parent, text='Gemini 3.8 Flash TTS · mẫu cho preview').pack(anchor='w', pady=(0, 8))
        key_row = ttk.Frame(parent); key_row.pack(fill='x', pady=(0, 6))
        ttk.Label(key_row, textvariable=self.tts_key_status).pack(side='left', fill='x', expand=True)
        ttk.Button(key_row, text='Đọc lại key', command=self.refresh_tts_keys).pack(side='right')
        self.tts_text = tk.Text(parent, height=7, wrap='word', bg='#202633', fg='#e6e8ee', insertbackground='white')
        self.tts_text.pack(fill='both', expand=True)
        ttk.Button(parent, text='Lấy lời của cảnh đang chọn', command=self.fill_tts_text).pack(fill='x', pady=4)
        self.tts_voice = tk.StringVar(value='Aoede')
        self.tts_model = tk.StringVar(value=GEMINI_TTS_MODEL)
        ttk.Label(parent, text='Giọng / model Gemini:').pack(anchor='w')
        ttk.Combobox(parent, textvariable=self.tts_voice, values=['Aoede', 'Kore', 'Puck', 'Charon', 'Fenrir'], state='readonly').pack(fill='x')
        ttk.Entry(parent, textvariable=self.tts_model, state='readonly').pack(fill='x', pady=4)
        self.build_voice_controls(parent)
        self.tts_button = ttk.Button(parent, text='Tạo đoạn mẫu (Gemini API)', command=self.generate_tts_sample)
        self.tts_button.pack(fill='x')
        ttk.Button(parent, text='Mở Vietnamese Multi-Voice Studio', command=lambda: webbrowser.open(STUDIO_APP)).pack(fill='x', pady=4)
        ttk.Button(parent, text='Nhập audio tải từ AI Studio', command=self.import_audio_sample).pack(fill='x')
        ttk.Button(parent, text='Nghe bản gốc', command=self.listen_original).pack(fill='x', pady=4)
        ttk.Button(parent, text='Nghe bản đã chỉnh', command=self.listen_sample).pack(fill='x', pady=4)
        ttk.Button(parent, text='Dừng nghe', command=self._stop_audio).pack(fill='x')
        ttk.Label(parent, text='Lịch sử mẫu trong phiên (tối đa 8):').pack(anchor='w', pady=(8, 2))
        self.sample_history = ttk.Combobox(parent, state='readonly')
        self.sample_history.pack(fill='x')
        self.sample_history.bind('<<ComboboxSelected>>', self.select_studio_sample)
        self.fit_audio = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text='Đặt thời lượng cảnh bằng đoạn audio', variable=self.fit_audio).pack(anchor='w', pady=6)
        ttk.Button(parent, text='Gắn mẫu → cảnh đang chọn', command=self.attach_audio_sample).pack(fill='x')
        ttk.Label(parent, textvariable=self.tts_status, wraplength=330).pack(fill='x', pady=8)
        ttk.Label(parent, text='Nút tạo gửi đoạn chữ tới Gemini và dùng quota API đã cấu hình. Audio chỉ là reference cho Kaggle.', wraplength=330).pack(fill='x')
        self.refresh_tts_keys()

    def gemini_keys(self):
        import yaml
        from brain.models import load_gemini_keys
        config = Path(__file__).resolve().parent / 'config.yaml'
        cfg = yaml.safe_load(config.read_text(encoding='utf-8')) if config.exists() else {}
        return load_gemini_keys(cfg)

    def refresh_tts_keys(self):
        keys = self.gemini_keys()
        source = Path.home() / 'Downloads' / 'gemini.txt'
        where = 'Downloads/gemini.txt' if source.is_file() else 'env/config'
        self.tts_key_status.set(f'{len(keys)} Gemini key sẵn sàng · {where}' if keys else 'Chưa có Gemini key')

    def fill_tts_text(self):
        self.tts_text.delete('1.0', 'end')
        self.tts_text.insert('1.0', self.scenes[self.play_idx].get('narration', ''))

    def sample_work(self, task, on_success=None):
        if self._tts_busy:
            return
        self.pause(); self._tts_busy = True; self.tts_button.configure(state='disabled')
        queue = Queue()
        def worker():
            try:
                queue.put((True, task()))
            except Exception:
                queue.put((False, 'Không tạo/đọc được audio. Kiểm tra key, model, quota hoặc định dạng file; không tự gọi lại.'))
        def poll():
            if self._closed:
                return
            try:
                ok, value = queue.get_nowait()
            except Empty:
                self.win.after(150, poll); return
            self._tts_busy = False; self.tts_button.configure(state='normal')
            if ok:
                if on_success:
                    on_success(value)
                else:
                    from brain.voice_studio import DEFAULT_PROCESSING
                    self.receive_studio_sample(dict(dry=value, wet=value, recipe=dict(source='imported', processing=DEFAULT_PROCESSING.copy())))
            else:
                self.tts_status.set(value)
        threading.Thread(target=worker, daemon=True).start()
        self.win.after(150, poll)

    def generate_tts_sample(self):
        from brain.voice_studio import generate_sample_with_keys, audio_duration, process_sample
        text = self.tts_text.get('1.0', 'end').strip()
        if not text or len(text) > 1500:
            return messagebox.showwarning('TTS mẫu', 'Nhập 1–1500 ký tự để thử một đoạn ngắn.')
        keys = self.gemini_keys()
        if not keys:
            self.tts_status.set('Chưa có Gemini API key. Cấu hình GEMINI_API_KEY hoặc nhập audio từ AI Studio.'); return
        settings = self.studio_settings()
        settings.update(text=text, source='gemini')
        out = self.project_dir / '.preview_cache' / 'tts' / (uuid.uuid4().hex + '.wav')
        self.tts_status.set('Đang tạo một đoạn mẫu bằng Gemini…')
        def task():
            _path, available, total = generate_sample_with_keys(text, out, keys, settings)
            dry = (out, audio_duration(out))
            wet = process_sample(out, out.with_name(out.stem + '_mix.wav'), settings['processing'])
            return dict(dry=dry, wet=wet, recipe=settings, key_status=(available, total))
        def done(result):
            available, total = result.pop('key_status')
            self.tts_key_status.set(f'{available}/{total} Gemini key đang sẵn sàng · Downloads/gemini.txt')
            self.receive_studio_sample(result)
        self.sample_work(task, done)

    def import_audio_sample(self):
        from brain.local_audio import ffmpeg_binary
        import subprocess
        name = filedialog.askopenfilename(filetypes=[('Audio mẫu', '*.wav *.mp3 *.m4a *.ogg *.flac')])
        if not name:
            return
        out = self.project_dir / '.preview_cache' / 'tts' / (uuid.uuid4().hex + '.wav')
        def task():
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([ffmpeg_binary(), '-v', 'error', '-i', name, '-vn', '-ac', '1', '-ar', '24000', str(out)],
                           check=True, capture_output=True, timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            with wave.open(str(out)) as audio:
                duration = audio.getnframes() / audio.getframerate()
            if duration <= 0:
                raise ValueError('Audio rỗng')
            return out, duration
        self.sample_work(task)

    def listen_sample(self):
        if self._tts_sample:
            self.pause()
            self._native_audio.play(self._tts_sample[0], duration=self._tts_sample[1])

    def attach_audio_sample(self):
        if self._tts_busy:
            self.tts_status.set('Chờ tạo/chỉnh audio hoàn tất trước khi gắn mẫu.'); return
        if not self._tts_sample:
            self.tts_status.set('Tạo hoặc nhập audio trước khi gắn.'); return
        if self._render_busy:
            self.tts_status.set('Chờ dựng preview hoàn tất trước khi gắn audio.'); return
        source, duration = self._tts_sample
        dest = self.project_dir / 'audio' / ('reference_' + uuid.uuid4().hex + '.wav')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        self._store_notes()
        scene = self.scenes[self.play_idx]
        scene['reference_audio'] = dest.relative_to(self.project_dir).as_posix()
        import copy
        scene['voice_recipe'] = copy.deepcopy(self._tts_recipe)
        self.proj['audio'][scene['scene_id']] = str(dest)
        if self.fit_audio.get():
            scene['estimated_duration_sec'] = duration
        self._refresh_all()
        self.tts_status.set(f"Đã gắn mẫu vào {scene['scene_id']}. Lưu profile để giữ lựa chọn. Sub ước tính cần nghe duyệt; SRT nhập giữ mốc cũ.")
