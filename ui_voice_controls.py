"""Desktop voice studio controls, using the pipeline's shared audio backend."""
import copy
import json
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from brain.voice_studio import LANGUAGES, ACCENTS, PERSONAS, TONES, DEFAULT_PROCESSING, RANGES, process_sample


class VoiceStudioControls:
    def build_voice_controls(self, parent):
        self._tts_dry = None
        self._tts_recipe = {}
        self._tts_history = []
        self.voice_language = tk.StringVar(value='Tiếng Việt')
        self.voice_accent = tk.StringVar(value='Tự nhiên')
        self.voice_persona = tk.StringVar(value='Tự nhiên')
        self.voice_tone = tk.StringVar(value='Trung tính')
        self.voice_direction = tk.StringVar()
        studio_tabs = ttk.Notebook(parent)
        studio_tabs.pack(fill='x', pady=6)
        voice_box = ttk.Frame(studio_tabs, padding=8)
        processing = ttk.Frame(studio_tabs, padding=8)
        studio_tabs.add(voice_box, text='Ngôn ngữ & giọng')
        studio_tabs.add(processing, text='Bộ chỉnh âm')
        for label, var, choices in [('Ngôn ngữ', self.voice_language, LANGUAGES),
                                    ('Vùng giọng Việt', self.voice_accent, ACCENTS),
                                    ('Kiểu thể hiện', self.voice_persona, PERSONAS),
                                    ('Sắc thái', self.voice_tone, TONES)]:
            row = ttk.Frame(voice_box); row.pack(fill='x', pady=3)
            ttk.Label(row, text=label, width=15).pack(side='left')
            combo = ttk.Combobox(row, textvariable=var, values=list(choices), state='readonly', width=22)
            combo.pack(side='left', fill='x', expand=True)
            if var is self.voice_persona:
                combo.bind('<<ComboboxSelected>>', lambda e: self.tts_voice.set(PERSONAS[self.voice_persona.get()][0]))
        ttk.Label(voice_box, text='Chỉ dẫn riêng (không đọc thành lời):').pack(anchor='w', pady=(5, 0))
        ttk.Entry(voice_box, textvariable=self.voice_direction).pack(fill='x', pady=4)
        ttk.Label(voice_box, text='Nhập lời bằng ngôn ngữ đã chọn. Vùng giọng là chỉ dẫn cần nghe duyệt, không tự dịch.', wraplength=300).pack(fill='x')
        self.voice_processing = {}
        labels = dict(speed='Tốc độ ×', pitch='Cao độ · bán âm', bass='Bass · dB', treble='Treble · dB', reverb='Vang nhẹ · %', volume='Âm lượng · %')
        for key, default in DEFAULT_PROCESSING.items():
            var = tk.DoubleVar(value=default); self.voice_processing[key] = var
            row = ttk.Frame(processing); row.pack(fill='x')
            ttk.Label(row, text=labels[key]).pack(side='left')
            output = tk.StringVar(value=f'{default:.2f}')
            ttk.Label(row, textvariable=output, width=7, anchor='e').pack(side='right')
            def changed(*args, v=var, out=output):
                out.set(f'{v.get():.2f}')
                if self._tts_sample:
                    self.tts_status.set('Thông số vừa đổi; bấm Áp dụng để nghe bản mới. Bản đã tạo được giữ nguyên.')
            var.trace_add('write', changed)
            lo, hi = RANGES[key]
            ttk.Scale(processing, from_=lo, to=hi, variable=var).pack(fill='x', pady=(0, 4))
        row = ttk.Frame(processing); row.pack(fill='x')
        ttk.Button(row, text='Khôi phục', command=self.reset_voice_processing).pack(side='left')
        ttk.Button(row, text='Áp dụng · không gọi API', command=self.apply_voice_processing).pack(side='right')
        ttk.Label(processing, text='Tốc độ và cao độ chỉnh độc lập. Vang là echo nhẹ; bản gốc luôn được giữ.', wraplength=300).pack(fill='x', pady=5)
        row = ttk.Frame(parent); row.pack(fill='x', pady=4)
        ttk.Button(row, text='Lưu thiết lập', command=self.save_voice_preset).pack(side='left')
        ttk.Button(row, text='Nạp thiết lập', command=self.load_voice_preset).pack(side='right')

    def studio_settings(self):
        return dict(language=self.voice_language.get(), accent=self.voice_accent.get(),
                    persona=self.voice_persona.get(), tone=self.voice_tone.get(),
                    direction=self.voice_direction.get(), voice=self.tts_voice.get(),
                    model='gemini-3.8-flash-tts', processing={k: round(v.get(), 3) for k, v in self.voice_processing.items()})

    def set_studio_settings(self, settings):
        for name, var, choices in [('language', self.voice_language, LANGUAGES), ('accent', self.voice_accent, ACCENTS),
                                    ('persona', self.voice_persona, PERSONAS), ('tone', self.voice_tone, TONES)]:
            value = settings.get(name)
            if value in choices:
                var.set(value)
        self.voice_direction.set(settings.get('direction', ''))
        if settings.get('voice') in ('Aoede', 'Kore', 'Puck', 'Charon', 'Fenrir'):
            self.tts_voice.set(settings['voice'])
        from brain.voice_studio import validate_processing
        values = validate_processing(settings.get('processing', {}))
        for key, value in values.items():
            self.voice_processing[key].set(value)

    def reset_voice_processing(self):
        for key, value in DEFAULT_PROCESSING.items():
            self.voice_processing[key].set(value)

    def save_voice_preset(self):
        from brain.profile import write_json
        try:
            write_json(self.project_dir / 'voice_studio_settings.json', self.studio_settings())
            self.tts_status.set('Đã lưu thiết lập cho dự án. Thông số thực tế của mẫu sẽ được lưu riêng khi gắn cảnh.')
        except Exception as exc:
            messagebox.showerror('Thiết lập giọng', str(exc))

    def load_voice_preset(self):
        try:
            settings = json.loads((self.project_dir / 'voice_studio_settings.json').read_text(encoding='utf-8'))
            self.set_studio_settings(settings)
            self.tts_status.set('Đã nạp thiết lập. Tạo lại cho đổi cách đọc; Áp dụng cho đổi âm thanh local.')
        except Exception:
            self.tts_status.set('Chưa có thiết lập hợp lệ đã lưu cho dự án này.')

    def receive_studio_sample(self, result):
        self._tts_dry, self._tts_sample, self._tts_recipe = result['dry'], result['wet'], result['recipe']
        self._tts_history.insert(0, copy.deepcopy(result))
        self._tts_history = self._tts_history[:8]
        self.sample_history.configure(values=[f"{i+1}. {x['recipe'].get('language', 'Audio nhập')} · {x['wet'][1]:.2f}s" for i, x in enumerate(self._tts_history)])
        self.sample_history.current(0)
        self.tts_status.set(f'Bản đã chỉnh sẵn sàng: {self._tts_sample[1]:.2f}s. Nghe so sánh hoặc gắn vào cảnh.')

    def select_studio_sample(self, event=None):
        index = self.sample_history.current()
        if index < 0:
            return
        result = self._tts_history[index]
        self.pause()
        self._tts_dry, self._tts_sample, self._tts_recipe = result['dry'], result['wet'], copy.deepcopy(result['recipe'])
        self.set_studio_settings(self._tts_recipe)
        if 'text' in self._tts_recipe:
            self.tts_text.delete('1.0', 'end'); self.tts_text.insert('1.0', self._tts_recipe['text'])
        self.tts_status.set(f'Đã chọn mẫu {index+1}: {self._tts_sample[1]:.2f}s.')

    def listen_original(self):
        if self._tts_dry:
            self.pause(); self._native_audio.play(self._tts_dry[0], duration=self._tts_dry[1])

    def apply_voice_processing(self):
        if self._tts_busy:
            return
        if not self._tts_dry:
            self.tts_status.set('Tạo hoặc nhập audio trước khi chỉnh.'); return
        dry = self._tts_dry
        recipe = copy.deepcopy(self._tts_recipe)
        recipe['processing'] = self.studio_settings()['processing']
        out = self.project_dir / '.preview_cache' / 'tts' / (uuid.uuid4().hex + '.wav')
        self.tts_status.set('Đang xử lý bản sao audio trên máy…')
        def task():
            return dict(dry=dry, wet=process_sample(dry[0], out, recipe['processing']), recipe=recipe)
        self.sample_work(task, self.receive_studio_sample)
