"""The script/asset preparation pane inside the existing Tk desktop app."""
from pathlib import Path
from queue import Queue, Empty
import threading
from tkinter import ttk, Text, StringVar, filedialog, messagebox, END

from brain.assembly import parse_script, scan_library, suggest_assets, assemble_project, tokens


class AssemblyPane:
    def __init__(self, app, parent, root):
        self.app, self.parent, self.root = app, parent, Path(root)
        self.catalog, self.scenes = [], []
        self.script_snapshot = ""
        self.busy = False
        self.research_context = []
        self.title = StringVar(value="Dự án preview")
        self.folder = StringVar(value=str(self.root / "downloads"))
        self.filter = StringVar()
        self.ratio = StringVar(value="auto")
        self.status = StringVar(value="1. Nhập kịch bản → 2. Đọc kho → 3. Ghép cảnh → 4. Tạo preview")
        top = ttk.Frame(parent, padding=8); top.pack(fill="x")
        ttk.Label(top, text="Tên hồ sơ:").pack(side="left")
        ttk.Entry(top, textvariable=self.title).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Combobox(top, textvariable=self.ratio,
                     values=["auto", "9:16", "16:9", "1:1"],
                     state="readonly", width=9).pack(side="left")
        ttk.Label(top, text="auto = theo asset đầu tiên", style="Muted.TLabel").pack(side="left", padx=(6, 0))
        split = ttk.Panedwindow(parent, orient="horizontal"); split.pack(fill="both", expand=True)
        left = ttk.Frame(split, padding=8); right = ttk.Frame(split, padding=8)
        split.add(left, weight=1); split.add(right, weight=1)
        ttk.Label(left, text="KỊCH BẢN · ## Tên cảnh hoặc mỗi đoạn cách một dòng trống").pack(anchor="w")
        self.script = Text(left, height=8, wrap="word", bg="#202633", fg="#e6e8ee", insertbackground="white")
        self.script.pack(fill="both", expand=True, pady=6)
        self.research_label = StringVar(value="Chưa chọn nguồn bài viết / bình luận")
        ttk.Label(left, textvariable=self.research_label).pack(anchor="w")
        research_actions = ttk.Frame(left); research_actions.pack(fill="x")
        ttk.Button(research_actions, text="Xem nguồn nghiên cứu", command=self.view_research).pack(side="left")
        ttk.Button(research_actions, text="Bỏ nguồn đã chọn", command=self.clear_research).pack(side="left")
        actions = ttk.Frame(left); actions.pack(fill="x")
        ttk.Button(actions, text="Nhập .md / .txt", command=self.import_script).pack(side="left")
        ttk.Button(actions, text="Tách / cập nhật cảnh", command=self.split_script).pack(side="left", padx=5)
        self.scene_tree = ttk.Treeview(left, columns=("scene", "asset", "reason"), show="headings", height=7)
        for key, label, width in [("scene", "Cảnh / ý đồ hình", 190), ("asset", "Asset đã ghép", 140), ("reason", "Lý do gợi ý", 200)]:
            self.scene_tree.heading(key, text=label); self.scene_tree.column(key, width=width)
        self.scene_tree.pack(fill="both", expand=True, pady=6)
        ttk.Label(right, text="KHO ASSET CHUNG · dùng file đã tải ở mục 1").pack(anchor="w")
        row = ttk.Frame(right); row.pack(fill="x", pady=6)
        ttk.Entry(row, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Chọn kho", command=self.choose_folder).pack(side="left")
        row = ttk.Frame(right); row.pack(fill="x")
        ttk.Button(row, text="Đọc lại kho", command=self.scan).pack(side="left")
        ttk.Button(row, text="Quét mô tả AI (Groq)", command=self.scan_ai).pack(side="left", padx=5)
        ttk.Entry(right, textvariable=self.filter).pack(fill="x", pady=6)
        self.filter.trace_add("write", lambda *_: self.show_assets())
        self.asset_tree = ttk.Treeview(right, columns=("title", "type", "caption"), show="headings", height=10)
        for key, label, width in [("title", "Tên asset", 190), ("type", "Loại", 55), ("caption", "Mô tả đã có", 230)]:
            self.asset_tree.heading(key, text=label); self.asset_tree.column(key, width=width)
        self.asset_tree.pack(fill="both", expand=True)
        self.asset_tree.bind("<Double-1>", lambda _: self.assign())
        ttk.Button(right, text="Gán asset đang chọn → cảnh đang chọn", command=self.assign).pack(fill="x", pady=5)
        ttk.Button(right, text="Gợi ý các cảnh còn trống từ tên / mô tả", command=self.suggest).pack(fill="x")
        ttk.Label(right, text="Gợi ý từ khóa cần duyệt lại hình ảnh. Quét AI gửi asset tới Groq và dùng quota của bạn.", wraplength=440).pack(fill="x", pady=5)
        bottom = ttk.Frame(parent, padding=8); bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status, wraplength=750).pack(side="left", fill="x", expand=True)
        ttk.Button(bottom, text="Tạo hồ sơ → xem trong app", style="Green.TButton", command=self.create).pack(side="right")

    def add_research(self, post):
        self.research_context = [p for p in self.research_context if (p['platform'], p['post_id']) != (post['platform'], post['post_id'])]
        self.research_context.append(post)
        self.research_label.set(f"{len(self.research_context)} nguồn; {sum(len(p['comments']) for p in self.research_context)} bình luận sẽ đi cùng hồ sơ")

    def clear_research(self):
        self.research_context = []
        self.research_label.set("Chưa chọn nguồn bài viết / bình luận")

    def view_research(self):
        import tkinter as tk
        window = tk.Toplevel(self.parent); window.title("Nguồn nghiên cứu đã chọn")
        text = Text(window, wrap="word", width=90, height=28); text.pack(fill="both", expand=True)
        for p in self.research_context:
            text.insert(END, p['url'] + '\n' + p['text'] + '\n\n')
            for c in p['comments']:
                text.insert(END, c['text'] + '\n\n')
        text.configure(state="disabled")

    def work(self, fn, callback):
        if self.busy:
            return messagebox.showinfo("Đang xử lý", "Chờ tác vụ kho / hồ sơ hiện tại hoàn tất.")
        self.busy = True
        queue = Queue()
        def worker():
            try: queue.put((True, fn()))
            except Exception as exc: queue.put((False, str(exc)))
        def poll():
            try: ok, result = queue.get_nowait()
            except Empty:
                self.parent.after(100, poll); return
            self.busy = False
            if ok: callback(result)
            else:
                self.status.set(result)
                messagebox.showerror("Không hoàn tất", result)
        threading.Thread(target=worker, daemon=True).start()
        self.parent.after(100, poll)

    def import_script(self):
        path = filedialog.askopenfilename(filetypes=[("Kịch bản", "*.md *.txt")])
        if path:
            try:
                text = Path(path).read_text(encoding="utf-8-sig")
                self.script.delete("1.0", END); self.script.insert("1.0", text)
            except Exception as exc: messagebox.showerror("Kịch bản", str(exc))

    def split_script(self):
        if self.scenes and not messagebox.askyesno("Tách lại", "Tách lại sẽ thay các cảnh và ghép asset trong bản nháp này. Tiếp tục?"):
            return
        try:
            text = self.script.get("1.0", END).strip()
            scenes = parse_script(text)
            self.scenes, self.script_snapshot = scenes, text
            self.show_scenes()
        except Exception as exc: messagebox.showwarning("Kịch bản", str(exc))

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder.get())
        if folder: self.folder.set(folder); self.scan()

    def scan(self):
        folder = self.folder.get()
        self.status.set("Đang đọc file và manifest trong kho…")
        def done(catalog):
            self.catalog = catalog; self.show_assets()
            self.status.set(f"{len(catalog)} asset. Chọn cảnh + asset để gán tay hoặc dùng gợi ý từ khóa.")
        self.work(lambda: scan_library(folder, self.root), done)

    def scan_ai(self):
        if messagebox.askyesno("Quét AI", "Gửi ảnh / keyframe trong kho đã chọn tới Groq để tạo mô tả? Thao tác dùng API/quota đã cấu hình. Xong hãy bấm Đọc lại kho."):
            self.app.run("ai", ["scan", "--dir", self.folder.get()])

    def show_assets(self):
        self.asset_tree.delete(*self.asset_tree.get_children())
        query = tokens(self.filter.get())
        for a in self.catalog:
            if query and not query <= tokens(a["title"] + " " + str(a.get("caption", ""))): continue
            self.asset_tree.insert("", END, iid=a["asset_id"], values=(a["title"], a["type"], a.get("caption", "")))

    def show_scenes(self):
        self.scene_tree.delete(*self.scene_tree.get_children())
        names = {a["asset_id"]: a["title"] for a in self.catalog}
        for s in self.scenes:
            self.scene_tree.insert("", END, iid=s["scene_id"], values=(s["visual_intent"][:80], ", ".join(names.get(a, a) for a in s["asset_ids"]), s.get("match_reason", "")))
        self.status.set(f"{len(self.scenes)} cảnh · {sum(bool(s['asset_ids']) for s in self.scenes)} đã ghép · cần duyệt lại trước khi bàn giao")

    def suggest(self):
        if not self.scenes: self.split_script()
        if not self.scenes or not self.catalog: return messagebox.showinfo("Thiếu đầu vào", "Nhập kịch bản và Đọc lại kho trước.")
        self.scenes = suggest_assets(self.scenes, self.catalog); self.show_scenes()

    def assign(self):
        scenes, assets = self.scene_tree.selection(), self.asset_tree.selection()
        if not scenes or not assets: return messagebox.showinfo("Chọn cảnh và asset", "Chọn một dòng ở mỗi bảng trước khi gán.")
        for s in self.scenes:
            if s["scene_id"] == scenes[0]:
                s.update(asset_ids=[assets[0]], status="ready", match_method="manual", match_reason="Người dùng chọn")
        self.show_scenes(); self.scene_tree.selection_set(scenes[0])

    def create(self):
        if not self.scenes: self.split_script()
        if not self.scenes: return
        if self.script.get("1.0", END).strip() != self.script_snapshot:
            return messagebox.showwarning("Kịch bản đã đổi", "Bấm Tách / cập nhật cảnh trước khi tạo hồ sơ.")
        import copy
        scenes, catalog = copy.deepcopy(self.scenes), copy.deepcopy(self.catalog)
        script, title, ratio = self.script_snapshot, self.title.get(), self.ratio.get()
        self.status.set("Đang đóng gói asset đã ghép; không sao chép toàn bộ kho…")
        def done(project):
            self.status.set(f"Đã tạo {project.name}")
            self.app.refresh_projects(); self.app.show_preview(project)
        research = copy.deepcopy(self.research_context)
        self.work(lambda: assemble_project(script, scenes, catalog, self.root / "outputs", title, ratio, research), done)
