"""Social research pane in the existing desktop application."""
import copy
import json
import threading
from queue import Queue, Empty
from tkinter import Text, StringVar, END, ttk, messagebox, filedialog
from core.social_research import ResearchStore, collect, connection_status


class ResearchPane:
    def __init__(self, app, parent, root):
        self.app, self.parent = app, parent
        self.store = ResearchStore(root / 'data' / 'research.db')
        self.platform = StringVar(value='reddit')
        self.limit = StringVar(value='100')
        self.status = StringVar()
        self.busy = False
        bar = ttk.Frame(parent, padding=8); bar.pack(fill='x')
        box = ttk.Combobox(bar, textvariable=self.platform, values=['reddit', 'youtube', 'facebook', 'threads'], state='readonly', width=12)
        box.pack(side='left')
        box.bind('<<ComboboxSelected>>', lambda e: self.status.set(connection_status(self.platform.get())))
        ttk.Label(bar, text='Bình luận/bài:').pack(side='left', padx=8)
        ttk.Spinbox(bar, from_=1, to=1000, textvariable=self.limit, width=6).pack(side='left')
        self.fetch_button = ttk.Button(bar, text='Lấy bài & bình luận', command=self.fetch)
        self.fetch_button.pack(side='left', padx=8)
        ttk.Button(bar, text='Kết nối API', command=self.configure_api).pack(side='left')
        ttk.Button(bar, text='Xuất JSON', command=self.export).pack(side='left')
        ttk.Button(bar, text='Đưa bài / bình luận chọn → Kịch bản', command=self.transfer).pack(side='right')
        ttk.Label(parent, text='Mỗi dòng một URL / ID, tối đa 20 bài. Facebook: PageID_PostID; Threads: ID số từ API.').pack(anchor='w', padx=8)
        self.urls = Text(parent, height=3, bg='#202633', fg='#e6e8ee', insertbackground='white')
        self.urls.pack(fill='x', padx=8, pady=6)
        split = ttk.Panedwindow(parent, orient='horizontal'); split.pack(fill='both', expand=True, padx=8)
        left, right = ttk.Frame(split), ttk.Frame(split)
        split.add(left, weight=1); split.add(right, weight=2)
        self.posts = ttk.Treeview(left, columns=('source', 'text', 'count', 'state'), show='headings', selectmode='browse')
        for key, label, width in [('source', 'Nguồn', 75), ('text', 'Bài viết', 210), ('count', 'Đã lấy', 60), ('state', 'Phạm vi', 80)]:
            self.posts.heading(key, text=label); self.posts.column(key, width=width)
        self.posts.pack(fill='both', expand=True)
        self.posts.bind('<<TreeviewSelect>>', self.show_post)
        self.detail = Text(right, height=5, wrap='word', bg='#202633', fg='#e6e8ee', state='disabled')
        self.detail.pack(fill='both', expand=True)
        ttk.Label(right, text='Ctrl / Shift để chọn nhiều bình luận; bỏ chọn để chuyển cả mẫu đã thu.').pack(anchor='w')
        self.comments = ttk.Treeview(right, columns=('author', 'text', 'parent'), show='headings', selectmode='extended')
        for key, label, width in [('author', 'Tác giả', 90), ('text', 'Bình luận', 320), ('parent', 'Trả lời ID', 95)]:
            self.comments.heading(key, text=label); self.comments.column(key, width=width)
        self.comments.pack(fill='both', expand=True)
        scroll = ttk.Scrollbar(right, orient='vertical', command=self.comments.yview)
        scroll.pack(side='right', fill='y'); self.comments.configure(yscrollcommand=scroll.set)
        self.comments.bind('<<TreeviewSelect>>', self.show_comment)
        ttk.Label(parent, textvariable=self.status, wraplength=1050, padding=8).pack(fill='x')
        self.status.set(connection_status(self.platform.get()))
        self.reload()

    def configure_api(self):
        import os
        import tkinter as tk
        from core.social_research import REQUIRED
        platform = self.platform.get()
        window = tk.Toplevel(self.parent); window.title('Kết nối ' + platform)
        ttk.Label(window, text='Chỉ lưu trong phiên app; đóng app sẽ xóa cấu hình vừa nhập.', padding=10).pack()
        entries = {}
        for name in REQUIRED[platform]:
            ttk.Label(window, text=name).pack(anchor='w', padx=10)
            entry = ttk.Entry(window, width=55, show='' if name.endswith('VERSION') else '*')
            entry.pack(padx=10, pady=5)
            entries[name] = entry
        def save():
            for name, entry in entries.items():
                value = entry.get().strip()
                if value:
                    os.environ[name] = value
            self.status.set(connection_status(platform)); window.destroy()
        ttk.Button(window, text='Áp dụng cho phiên này', command=save).pack(pady=10)

    def reload(self):
        self.rows = self.store.posts()
        self.posts.delete(*self.posts.get_children())
        for i, p in enumerate(self.rows):
            self.posts.insert('', END, iid=str(i), values=(p['platform'], p['text'][:120], p['retrieved_count'], p['completeness']))

    def current(self):
        selected = self.posts.selection()
        return self.rows[int(selected[0])] if selected else None

    def detail_text(self, text):
        self.detail.configure(state='normal'); self.detail.delete('1.0', END)
        self.detail.insert('1.0', text); self.detail.configure(state='disabled')

    def show_post(self, event=None):
        self.comments.delete(*self.comments.get_children())
        p = self.current()
        if not p:
            return
        self.detail_text(p['url'] + '\n' + p['text'])
        for i, c in enumerate(p['comments']):
            self.comments.insert('', END, iid=str(i), values=(c['author'], c['text'], c['parent_comment_id'] or ''))
        self.status.set(f"Đã lấy {p['retrieved_count']}; nguồn báo {p['reported_count']}; phạm vi {p['completeness']}. Ý kiến cộng đồng cần kiểm chứng.")

    def show_comment(self, event=None):
        p = self.current()
        selected = self.comments.selection()
        if p and selected:
            c = p['comments'][int(selected[-1])]
            self.detail_text(c['text'] + '\n\n' + (c['permalink'] or p['url']))

    def fetch(self):
        if self.busy:
            return
        urls = list(dict.fromkeys(x.strip() for x in self.urls.get('1.0', END).splitlines() if x.strip()))
        try:
            limit = int(self.limit.get())
            if not 1 <= limit <= 1000 or not 1 <= len(urls) <= 20:
                raise ValueError()
        except ValueError:
            return messagebox.showwarning('Dữ liệu đầu vào', 'Nhập 1–20 URL / ID và giới hạn 1–1000.')
        platform = self.platform.get()
        self.busy = True; self.fetch_button.configure(state='disabled')
        self.status.set('Đang thu thập…')
        queue = Queue()
        def worker():
            for index, url in enumerate(urls):
                try:
                    post = collect(platform, url, limit)
                    self.store.save(post)
                    queue.put(('progress', f"{index + 1}/{len(urls)}: đã lấy {post['retrieved_count']} bình luận"))
                except Exception as exc:
                    queue.put(('error', f'Bài {index + 1}: {exc}'))
            queue.put(('done', ''))
        errors = []
        def poll():
            if not self.parent.winfo_exists():
                return
            try:
                while True:
                    kind, text = queue.get_nowait()
                    if kind == 'done':
                        self.busy = False; self.fetch_button.configure(state='normal'); self.reload()
                        self.status.set(f'Hoàn tất {len(urls) - len(errors)}/{len(urls)} bài.' + (' ' + ' | '.join(errors) if errors else ''))
                        return
                    if kind == 'error':
                        errors.append(text)
                    self.status.set(text)
            except Empty:
                self.parent.after(100, poll)
        threading.Thread(target=worker, daemon=True).start()
        self.parent.after(100, poll)

    def chosen(self):
        p = self.current()
        if not p:
            messagebox.showinfo('Nguồn nghiên cứu', 'Chọn một bài viết trước.'); return None
        p = copy.deepcopy(p)
        ids = self.comments.selection()
        if ids:
            p['comments'] = [p['comments'][int(i)] for i in ids]
        p['selected_count'] = len(p['comments'])
        return p

    def transfer(self):
        p = self.chosen()
        if p:
            self.app.assembly.add_research(p)
            self.app.sections.select(self.app.creation_tab)
            self.app.creation_pages.select(self.app.script_host)

    def export(self):
        p = self.chosen()
        if not p:
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if path:
            try:
                from pathlib import Path
                Path(path).write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding='utf-8')
            except OSError as exc:
                messagebox.showerror('Xuất dữ liệu', str(exc))
