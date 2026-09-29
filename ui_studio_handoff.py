"""Optional desktop adapter. Shared studio_bridge never imports Tk."""
import copy
from pathlib import Path
from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from studio_bridge.project import ROLES, add_cue, export_bundle, from_preview, read, register, validate, write
from studio_bridge.kaggle import inspect


class StudioHandoff:
    def __init__(self, parent, project_dir):
        self.root = Path(project_dir)
        self.project = None
        self.busy = False
        self.win = tk.Toplevel(parent)
        self.win.title("Flow3 • Tài nguyên và bàn giao Kaggle")
        self.win.geometry("980x680")
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        box = ttk.Frame(self.win, padding=12); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Bộ nhận dự án chung • không thay đổi Colab / ZIP cũ", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(box, text="TTS preview vẫn là mẫu. Thêm tài nguyên vào dự án rồi gắn vai trò và mốc phát theo cảnh.").pack(anchor="w", pady=6)
        self.tree = ttk.Treeview(box, columns=("type", "scene", "file", "timing"), show="headings")
        for key, label, width in (("type", "Vai trò", 145), ("scene", "Cảnh", 110), ("file", "File / mã tài nguyên", 400), ("timing", "Mốc / thời lượng", 180)):
            self.tree.heading(key, text=label); self.tree.column(key, width=width)
        self.tree.pack(fill="both", expand=True)
        form = ttk.Frame(box); form.pack(fill="x", pady=10)
        self.role = tk.StringVar(value="sfx"); self.scene = tk.StringVar()
        ttk.Label(form, text="Vai trò").grid(row=0, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.role, values=["sfx", "music", "overlay_image", "overlay_video", "font", "voice_reference", "final_narration"], state="readonly", width=20).grid(row=1, column=0, padx=(0, 8))
        ttk.Label(form, text="Cảnh / neo bắt đầu").grid(row=0, column=1, sticky="w")
        self.scene_box = ttk.Combobox(form, textvariable=self.scene, state="readonly", width=18)
        self.scene_box.grid(row=1, column=1, padx=(0, 8))
        self.offset = tk.StringVar(value="0"); self.duration = tk.StringVar(value="1"); self.gain = tk.StringVar(value="-12")
        for col, (label, variable) in enumerate((("Lệch (giây)", self.offset), ("Dài (giây)", self.duration), ("Gain dB", self.gain)), 2):
            ttk.Label(form, text=label).grid(row=0, column=col, sticky="w")
            ttk.Entry(form, textvariable=variable, width=10).grid(row=1, column=col, padx=5)
        self.loop = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="Lặp audio", variable=self.loop).grid(row=1, column=5)
        row = ttk.Frame(box); row.pack(fill="x")
        ttk.Button(row, text="Thêm file + gán vai trò", command=self.add).pack(side="left")
        ttk.Button(row, text="Bỏ cue đã chọn", command=self.remove).pack(side="left", padx=6)
        ttk.Button(row, text="Kiểm tra", command=self.check).pack(side="left")
        ttk.Button(row, text="Xuất Studio ZIP mới", command=self.export).pack(side="right")
        ttk.Label(box, text="Bản v1 bỏ tiếng gốc của footage; voice cuối được gán riêng. Layer ảnh: giữa màn hình, rộng 30%. Hiệu ứng chưa hỗ trợ sẽ chặn bước chuẩn bị, không tự bỏ qua.", wraplength=930).pack(anchor="w", pady=8)
        self.status = tk.StringVar(value="Đang đồng bộ profile đã lưu…")
        ttk.Label(box, textvariable=self.status, wraplength=930).pack(fill="x")
        self.work(lambda: from_preview(self.root), self.loaded)

    def close(self):
        if self.busy:
            return messagebox.showinfo("Đang xử lý", "Chờ đóng gói / sao chép hoàn tất.", parent=self.win)
        self.win.destroy()

    def work(self, fn, done):
        if self.busy:
            return
        self.busy = True
        queue = Queue()
        def worker():
            try: queue.put((True, fn()))
            except Exception as exc: queue.put((False, str(exc)))
        def poll():
            try: ok, value = queue.get_nowait()
            except Empty:
                self.win.after(100, poll); return
            self.busy = False
            if ok: done(value)
            else:
                self.status.set(value)
                messagebox.showerror("Chưa hoàn tất", value, parent=self.win)
        threading.Thread(target=worker, daemon=True).start()
        self.win.after(100, poll)

    def loaded(self, project):
        self.project = project
        ids = [s["scene_id"] for s in project["scenes"]]
        self.scene_box.configure(values=ids)
        if self.scene.get() not in ids:
            self.scene.set(ids[0])
        self.tree.delete(*self.tree.get_children())
        assets = {a["asset_id"]: a for a in project["assets"]}
        for s in project["scenes"]:
            self.tree.insert("", "end", values=("cảnh", s["scene_id"], assets[s["asset_id"]]["path"], f"{s['duration_s']}s · dự kiến"))
            if s.get("final_audio_id"):
                self.tree.insert("", "end", values=("final_narration", s["scene_id"], assets[s["final_audio_id"]]["path"], "đo lại trên Kaggle"))
        for c in project["cues"]:
            self.tree.insert("", "end", iid=c["cue_id"], values=(c["role"], c["scene_id"], assets[c["asset_id"]]["path"], f"+{c['offset_s']}s / {c['duration_s']}s"))
        for a in project["assets"]:
            if {"font", "voice_reference"} & set(a["roles"]):
                self.tree.insert("", "end", values=(", ".join(a["roles"]), "tài nguyên", a["path"], "chưa áp dụng"))
        self.status.set(f"{len(project['assets'])} tài nguyên • {len(project['cues'])} cue. Thay đổi bàn giao đã lưu riêng; profile preview không đổi.")

    def add(self):
        if self.busy or self.project is None: return
        role, sid = self.role.get(), self.scene.get()
        path = filedialog.askopenfilename(parent=self.win, title="Chọn tài nguyên", filetypes=[("Tài nguyên", " ".join("*" + x for x in sorted(ROLES[role][1])))])
        if not path: return
        project = copy.deepcopy(self.project)
        offset, duration, gain, loop = self.offset.get(), self.duration.get(), self.gain.get(), self.loop.get()
        def task():
            aid = register(self.root, project, path, role, description=Path(path).stem)
            if role == "final_narration":
                next(s for s in project["scenes"] if s["scene_id"] == sid)["final_audio_id"] = aid
            elif role in ("music", "sfx", "overlay_image", "overlay_video"):
                add_cue(project, aid, role, sid, offset_s=offset, duration_s=duration, gain_db=gain, loop=loop)
            validate(self.root, project)
            write(self.root / "studio.project.json", project)
            return project
        self.work(task, self.loaded)

    def remove(self):
        if self.busy or self.project is None: return
        selected = set(self.tree.selection())
        project = copy.deepcopy(self.project)
        project["cues"] = [c for c in project["cues"] if c["cue_id"] not in selected]
        def task():
            write(self.root / "studio.project.json", project)
            return project
        self.work(task, self.loaded)

    def check(self):
        if self.project is None: return
        import json
        self.work(lambda: inspect(self.root, self.project), lambda r: messagebox.showinfo("Preflight • chưa phải render QC", json.dumps(r, ensure_ascii=False, indent=2), parent=self.win))

    def export(self):
        if self.busy or self.project is None: return
        path = filedialog.asksaveasfilename(parent=self.win, initialfile=self.root.name + ".studio.zip", defaultextension=".zip", filetypes=[("Studio bundle", "*.zip")])
        if path:
            self.status.set("Đang kiểm tra hash và đóng gói…")
            self.work(lambda: export_bundle(self.root, path), lambda _: self.status.set("Đã xuất: " + path + " • chưa upload, chưa render Kaggle."))
