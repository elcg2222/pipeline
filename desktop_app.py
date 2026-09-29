#!/usr/bin/env python
"""Cửa sổ desktop cục bộ cho Social Trend Pipeline.

Chạy: python desktop_app.py  (hoặc double-click "Pipeline App.vbs" / start_desktop_app.bat)
Hai mục trong một app: tìm asset và kịch bản/preview/handoff.
Remotion render nháp ở tiến trình nền, không mở trình duyệt trong luồng desktop.
"""
from __future__ import annotations

import json
import os
import sqlite3
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Tk, StringVar, Text, BooleanVar, Canvas, NW, TOP, BOTTOM
from tkinter import messagebox, ttk, filedialog, simpledialog
import tkinter as tk

DEFAULT_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
ROOT = Path(os.environ.get("PIPELINE_HOME", DEFAULT_ROOT)).resolve()
DB = ROOT / "data" / "pipeline.db"

# ============================================================ BẢNG MÀU
C = {
    "bg":          "#0f1117",   # nền chính
    "panel":       "#171a23",   # khung/card
    "panel2":      "#1d212c",   # dòng xen kẽ
    "border":      "#262b38",
    "accent":      "#4f8cff",   # xanh dương chủ đạo
    "accent_hov":  "#3a76e0",
    "green":       "#22c55e",
    "amber":       "#f59e0b",
    "red":         "#ef4444",
    "teal":        "#14b8a6",
    "purple":      "#a855f7",
    "text":        "#e6e8ee",
    "muted":       "#8b90a0",
    "heading":     "#10131b",
    "log_bg":      "#0a0c12",
}

# Trạng thái -> màu chữ trên bảng
STATE_COLOR = {
    "downloaded": C["green"],
    "qc_passed":  C["green"],
    "exported":   C["teal"],
    "dubbed":     C["teal"],
    "published":  C["teal"],
    "queued":     C["accent"],
    "discovered": C["muted"],
    "downloading": C["amber"],
    "qc_failed":  C["red"],
    "duplicate":  C["amber"],
    "rejected":   C["red"],
    "error":      C["red"],
}


def _apply_style(root: Tk) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.configure(bg=C["bg"])

    style.configure("TFrame", background=C["bg"])
    style.configure("Panel.TFrame", background=C["panel"])
    style.configure("TLabel", background=C["bg"], foreground=C["text"], font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=C["bg"], foreground=C["muted"], font=("Segoe UI", 9))
    style.configure("Title.TLabel", background=C["bg"], foreground=C["text"], font=("Segoe UI", 19, "bold"))
    style.configure("Sub.TLabel", background=C["bg"], foreground=C["muted"], font=("Segoe UI", 9))
    style.configure("Summary.TLabel", background=C["bg"], foreground=C["accent"], font=("Segoe UI", 10, "bold"))

    # Khung LabelFrame
    style.configure("TLabelframe", background=C["panel"], bordercolor=C["border"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=C["panel"], foreground=C["accent"], font=("Segoe UI", 10, "bold"))

    # Ô nhập / combobox
    style.configure("TEntry", fieldbackground="#202633", foreground=C["text"],
                    bordercolor=C["border"], insertcolor=C["text"], padding=6)
    style.configure("TCombobox", fieldbackground="#202633", background=C["panel"],
                    foreground=C["text"], arrowcolor=C["text"], bordercolor=C["border"], padding=6)
    style.map("TCombobox", fieldbackground=[("readonly", "#202633")],
              foreground=[("readonly", C["text"])])

    # Checkbutton
    style.configure("TCheckbutton", background=C["panel"], foreground=C["text"], font=("Segoe UI", 10))
    style.map("TCheckbutton", background=[("active", C["panel"])],
              foreground=[("active", C["text"])])

    # Nút bấm
    style.configure("Accent.TButton", background=C["accent"], foreground="#ffffff",
                    font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(12, 7))
    style.map("Accent.TButton", background=[("active", C["accent_hov"])])

    style.configure("Green.TButton", background=C["green"], foreground="#04170a",
                    font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(12, 7))
    style.map("Green.TButton", background=[("active", "#1db954")])

    style.configure("Ghost.TButton", background=C["panel2"], foreground=C["text"],
                    font=("Segoe UI", 10), borderwidth=0, padding=(12, 7))
    style.map("Ghost.TButton", background=[("active", C["border"])])

    style.configure("Warn.TButton", background=C["amber"], foreground="#1a1205",
                    font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(12, 7))
    style.map("Warn.TButton", background=[("active", "#e08e0b")])

    # Bảng Treeview
    style.configure("Treeview", background=C["panel"], fieldbackground=C["panel"],
                    foreground=C["text"], bordercolor=C["border"], rowheight=26,
                    font=("Segoe UI", 9))
    style.configure("Treeview.Heading", background="#232839", foreground=C["text"],
                    font=("Segoe UI", 9, "bold"), relief="flat", padding=6)
    style.map("Treeview", background=[("selected", "#2a3350")],
              foreground=[("selected", "#ffffff")])
    style.map("Treeview.Heading", background=[("active", "#2b3145")])

    # Scrollbar
    style.configure("Vertical.TScrollbar", background=C["panel2"], troughcolor=C["panel"],
                    bordercolor=C["panel"], arrowcolor=C["muted"])

    # Thanh trạng thái
    style.configure("Status.TLabel", background="#202633", foreground=C["accent"],
                    font=("Segoe UI", 9, "bold"))

    return style


class PipelineApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("Social Trend Pipeline")
        self.root.geometry("1220x780")
        self.root.minsize(980, 600)
        self.proc: subprocess.Popen | None = None
        self.preview = None
        self.output = ""
        self.status = StringVar(value="Đang kiểm tra công cụ…")
        self.summary = StringVar(value="Đang đọc dữ liệu…")
        self.style = _apply_style(self.root)
        self._build()
        self.refresh()
        self.root.after(400, self._startup_check)
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def _build(self):
        root = self.root
        outer = ttk.Frame(root, padding=16); outer.pack(fill=BOTH, expand=True)

        # ---------- Header ----------
        head = ttk.Frame(outer, style="Panel.TFrame", padding=16); head.pack(fill=X, pady=(0, 12))
        ttk.Label(head, text="🎬  Social Trend Pipeline", style="Title.TLabel").pack(anchor="w")
        ttk.Label(head, text="Tìm asset → Kịch bản → Preview local → Hồ sơ Kaggle · AI API chỉ khi được bật",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 8))
        ttk.Label(head, textvariable=self.summary, style="Summary.TLabel").pack(anchor="w")

        shell = outer
        self.sections = ttk.Notebook(shell)
        self.sections.pack(fill=BOTH, expand=True)
        outer = ttk.Frame(self.sections, padding=8)
        self.creation_tab = ttk.Frame(self.sections)
        self.sections.add(outer, text="  1 · Tìm asset theo chủ đề  ")
        self.sections.add(self.creation_tab, text="  2 · Kịch bản → Preview → Kaggle  ")
        asset_pages = ttk.Notebook(outer)
        asset_pages.pack(fill=BOTH, expand=True)
        media_host = ttk.Frame(asset_pages)
        research_host = ttk.Frame(asset_pages)
        asset_pages.add(media_host, text="Video & ảnh")
        asset_pages.add(research_host, text="Bài viết & bình luận")
        from ui_research import ResearchPane
        self.research = ResearchPane(self, research_host, ROOT)
        outer = media_host
        self.creation_pages = ttk.Notebook(self.creation_tab)
        self.creation_pages.pack(fill=BOTH, expand=True)
        self.script_host = ttk.Frame(self.creation_pages)
        self.preview_host = ttk.Frame(self.creation_pages)
        self.creation_pages.add(self.script_host, text="Kịch bản & ghép asset")
        self.creation_pages.add(self.preview_host, text="Preview & bàn giao")
        from ui_assembly import AssemblyPane
        self.assembly = AssemblyPane(self, self.script_host, ROOT)
        ttk.Label(self.preview_host, text="Nhập kịch bản để tạo hồ sơ, hoặc mở dự án đã có bên dưới.", padding=24).pack()

        # ---------- Hàng nút tác vụ video ----------
        actions = ttk.Frame(outer); actions.pack(fill=X, pady=(0, 10))
        ttk.Label(actions, text="VIDEO:", style="Muted.TLabel").pack(side=LEFT, padx=(0, 6))
        for label, command, st in [
            ("🔍 Quét nguồn", "discover", "Accent.TButton"),
            ("⬇ Tải video", "download", "Green.TButton"),
            ("✅ QC", "qc", "Ghost.TButton"),
            ("🚀 Chạy toàn bộ", "all", "Green.TButton"),
            ("♻ Xét lại rejected", "recheck", "Ghost.TButton"),
            ("🔁 Thử lại", "retry", "Ghost.TButton"),
        ]:
            ttk.Button(actions, text=label, style=st,
                       command=lambda c=command: self.run(c)).pack(side=LEFT, padx=(0, 6))

        # Nút mở Timeline Preview (kiểu CapCut)
        ttk.Button(actions, text="🎞 Xem trước timeline", style="Ghost.TButton",
                   command=lambda: self.sections.select(self.creation_tab)).pack(side=RIGHT)

        # ---------- Thêm URL ----------
        add = ttk.LabelFrame(outer, text="  Thêm video từ URL công khai  ", padding=10); add.pack(fill=X, pady=(0, 10))
        ttk.Label(add, text="Facebook · Instagram · Reddit · Discord · TikTok · YouTube · web khác — mỗi dòng một link, tối đa 20.",
                  style="Sub.TLabel").pack(anchor="w")
        self.urls = Text(add, height=3, font=("Consolas", 10), bg="#202633", fg=C["text"],
                         insertbackground=C["text"], relief="flat", padx=8, pady=6)
        self.urls.pack(fill=X, pady=8)
        ttk.Button(add, text="➕ Nhận diện và thêm vào hàng đợi", style="Accent.TButton",
                   command=self.add_urls).pack(anchor="w")

        # ---------- Đa định dạng ----------
        media = ttk.LabelFrame(outer, text="  Đa định dạng — ảnh / tin tức / video theo chủ đề  ", padding=10); media.pack(fill=X, pady=(0, 10))
        row = ttk.Frame(media); row.pack(fill=X)
        ttk.Label(row, text="Chủ đề:").pack(side=LEFT)
        self.media_query = ttk.Entry(row); self.media_query.pack(side=LEFT, fill=X, expand=True, padx=(6, 10))
        ttk.Label(row, text="Loại:").pack(side=LEFT)
        self.media_type = ttk.Combobox(row, state="readonly", width=12,
            values=["all", "image", "video", "news"]); self.media_type.current(0); self.media_type.pack(side=LEFT, padx=(6, 10))
        self.media_commercial = BooleanVar(value=True)
        ttk.Checkbutton(row, text="Chỉ thương mại", variable=self.media_commercial).pack(side=LEFT, padx=(0, 10))
        self.media_save = BooleanVar(value=True)
        ttk.Checkbutton(row, text="Tải file về máy", variable=self.media_save).pack(side=LEFT)
        row2 = ttk.Frame(media); row2.pack(fill=X, pady=(8, 0))
        ttk.Button(row2, text="🔎 Tìm + Tải ngay", style="Accent.TButton", command=self.run_media).pack(side=LEFT, padx=(0, 6))
        ttk.Button(row2, text="📰 Kéo tin RSS", style="Green.TButton",
                   command=lambda: self.run("media", ["crawl"])).pack(side=LEFT, padx=(0, 6))
        ttk.Button(row2, text="📊 Thống kê kho", style="Ghost.TButton",
                   command=lambda: self.run("media", ["stats"])).pack(side=LEFT)
        ttk.Button(row2, text="Dùng kho này → mục 2", style="Accent.TButton",
                   command=self.use_library).pack(side=RIGHT)

        # ---------- Dự án (project) + xem trước ----------
        proj = ttk.LabelFrame(self.creation_pages, text="  Dự án đã có — bấm đúp mở trong app  ", padding=6)
        self.creation_pages.add(proj, text="Mở dự án đã có")
        prow = ttk.Frame(proj); prow.pack(fill=X)
        self.project_list = ttk.Treeview(prow, columns=("id", "scenes", "dur", "updated"), show="headings", height=12)
        for col, label, width in [("id", "Project", 320), ("scenes", "Cảnh", 60),
                                  ("dur", "Thời lượng", 90), ("updated", "Sửa lúc", 130)]:
            self.project_list.heading(col, text=label); self.project_list.column(col, width=width, stretch=col == "id")
        self.project_list.pack(side=LEFT, fill=X, expand=True)
        pscroll = ttk.Scrollbar(prow, orient="vertical", command=self.project_list.yview); pscroll.pack(side=RIGHT, fill=Y)
        self.project_list.configure(yscrollcommand=pscroll.set)
        self.project_list.bind("<Double-1>", self.open_project_from_list)
        ttk.Button(proj, text="Mở thư mục dự án…", command=self.open_preview).pack(side=LEFT)
        ttk.Button(proj, text="↻ Làm mới", style="Ghost.TButton", command=self.refresh_projects).pack(side=RIGHT)
        self.refresh_projects()

        # ---------- Bảng + log ----------
        body = ttk.PanedWindow(outer, orient="vertical"); body.pack(fill=BOTH, expand=True)
        table_box = ttk.Frame(body, padding=3); body.add(table_box, weight=4)
        cols = ("platform", "title", "state", "attempts", "error", "updated")
        self.tree = ttk.Treeview(table_box, columns=cols, show="headings")
        for col, label, width in [("platform", "Nguồn", 90), ("title", "Video", 320), ("state", "Trạng thái", 100),
                                  ("attempts", "Lần thử", 60), ("error", "Lỗi gần nhất", 360), ("updated", "Cập nhật", 130)]:
            self.tree.heading(col, text=label); self.tree.column(col, width=width, stretch=col in {"title", "error"})
        # màu chữ theo trạng thái
        for st, color in STATE_COLOR.items():
            self.tree.tag_configure(st, foreground=color)
        self.tree.tag_configure("odd", background=C["panel2"])
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview); scroll.pack(side=RIGHT, fill=Y)
        self.tree.configure(yscrollcommand=scroll.set); self.tree.bind("<Double-1>", self.open_source)

        logbox = ttk.LabelFrame(body, text="  Tác vụ gần nhất  ", padding=5); body.add(logbox, weight=1)
        self.log = Text(logbox, height=7, state="disabled", font=("Consolas", 9),
                        bg=C["log_bg"], fg="#9fe6a0", insertbackground=C["text"], relief="flat", padx=8, pady=6)
        self.log.pack(fill=BOTH, expand=True)

        # ---------- Thanh trạng thái ----------
        statusbar = ttk.Frame(shell, style="Panel.TFrame", padding=(12, 6)); statusbar.pack(fill=X, pady=(10, 0))
        ttk.Label(statusbar, textvariable=self.status, style="Status.TLabel").pack(side=LEFT)

    # ------------------------------------------------------------ dữ liệu
    def db_rows(self):
        if not DB.exists(): return [], {}, {}
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in conn.execute("SELECT uid,platform,url,title,state,attempts,last_error,updated_at FROM videos ORDER BY updated_at DESC LIMIT 300")]
            states = dict(conn.execute("SELECT state,COUNT(*) FROM videos GROUP BY state").fetchall())
            platforms = dict(conn.execute("SELECT platform,COUNT(*) FROM videos GROUP BY platform").fetchall())
            return rows, states, platforms
        finally: conn.close()

    def refresh(self):
        try:
            rows, states, platforms = self.db_rows()
            self.summary.set(" | ".join([f"{k}: {v}" for k, v in sorted(platforms.items())]) or "Chưa có video")
            self.tree.delete(*self.tree.get_children())
            for i, r in enumerate(rows):
                stamp = time.strftime("%d/%m %H:%M", time.localtime(r["updated_at"] or 0)) if r["updated_at"] else "—"
                tags = [r["state"]] if r["state"] in STATE_COLOR else []
                if i % 2 == 1:
                    tags.append("odd")
                self.tree.insert("", END, iid=r["uid"], values=(r["platform"], r["title"] or r["uid"], r["state"], r["attempts"], (r["last_error"] or "").replace("\n", " ")[:200], stamp), tags=(r["url"],) + tuple(tags))
            if self.proc and self.proc.poll() is not None:
                code = self.proc.returncode
                self.proc = None
                self.status.set("✅ Hoàn tất — kho sẵn sàng cho mục 2" if code == 0 else f"Tác vụ lỗi (exit {code}) — xem log mục 1")
            self._set_log(self.output[-8000:])
        except Exception as exc:
            self.status.set(f"Không thể đọc dữ liệu: {exc}")
        self.root.after(2000, self.refresh)

    def _set_log(self, text: str):
        self.log.configure(state="normal"); self.log.delete("1.0", END); self.log.insert("1.0", text); self.log.configure(state="disabled")

    # ------------------------------------------------------------ kiểm tra công cụ khi mở
    def _startup_check(self):
        try:
            sys.path.insert(0, str(ROOT))
            from core.util import which
            tools = ["ffmpeg", "yt-dlp", "opencli", "f2"]
            ok = [t for t in tools if which(t)]
            miss = [t for t in tools if not which(t)]
            from brain.local_audio import ffmpeg_binary
            try:
                ffmpeg_binary()
                if "ffmpeg" in miss:
                    miss.remove("ffmpeg"); ok.append("ffmpeg (bundled, preview)")
            except RuntimeError:
                pass
            self.status.set("🟢 Công cụ sẵn sàng: " + ", ".join(ok) + (("  |  ⚠ thiếu: " + ", ".join(miss)) if miss else ""))
        except Exception as e:
            self.status.set(f"Không kiểm tra được công cụ: {e}")

    # ------------------------------------------------------------ chạy lệnh
    def run(self, command: str, extra: list[str] | None = None, urls: list[str] | None = None):
        if self.proc and self.proc.poll() is None:
            return messagebox.showwarning("Pipeline đang chạy", "Hãy chờ tác vụ hiện tại hoàn tất.")
        python = sys.executable if not getattr(sys, "frozen", False) else ("python.exe" if os.name == "nt" else "python3")
        args = [python, "run.py", command]
        for a in extra or []: args.append(a)
        for url in urls or []: args += ["--url", url]
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.proc = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", creationflags=flags)
            self.output = ""; self.status.set(f"⏳ Đang chạy: {command}")
            threading.Thread(target=self._collect_output, args=(self.proc,), daemon=True).start()
        except Exception as exc:
            messagebox.showerror("Không chạy được", str(exc))

    def _collect_output(self, proc: subprocess.Popen):
        if proc.stdout:
            for line in proc.stdout:
                self.output += line

    def add_urls(self):
        urls = [u.strip() for u in self.urls.get("1.0", END).splitlines() if u.strip()]
        if not urls or len(urls) > 20 or any(not u.startswith(("https://", "http://")) for u in urls):
            return messagebox.showwarning("URL không hợp lệ", "Nhập từ 1 đến 20 URL đầy đủ, mỗi dòng một link.")
        self.urls.delete("1.0", END); self.run("add", urls=urls)

    def run_media(self):
        q = self.media_query.get().strip()
        if not q:
            return messagebox.showwarning("Thiếu chủ đề", "Nhập từ khoá chủ đề để tìm.")
        mtype = self.media_type.get() or "all"
        extra = ["search", q, "--type", mtype]
        if self.media_commercial.get():
            extra.append("--commercial-only")
        if self.media_save.get():
            extra.append("--save")
        self.run("media", extra=extra)

    def open_source(self, _event):
        chosen = self.tree.selection()
        if chosen:
            webbrowser.open(self.tree.item(chosen[0], "tags")[0])

    def open_preview(self):
        """Mở cửa sổ Timeline Preview (kiểu CapCut) cho một project handoff."""
        out_root = ROOT / "outputs"
        default = str(out_root) if out_root.exists() else str(ROOT)
        proj_dir = filedialog.askdirectory(
            title="Chọn thư mục project_<id> để xem trước", initialdir=default)
        if not proj_dir:
            return
        try:
            self.show_preview(proj_dir)
        except Exception as exc:
            messagebox.showerror("Không mở được preview", str(exc))

    def refresh_projects(self):
        """Liệt kê các thư mục project trong outputs/ vào bảng."""
        self.project_list.delete(*self.project_list.get_children())
        out = ROOT / "outputs"
        if not out.exists():
            return
        try:
            import json as _json
            for d in sorted(out.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if not d.is_dir() or not (d / "scenes.json").exists():
                    continue
                scenes = _json.loads((d / "scenes.json").read_text(encoding="utf-8"))
                dur = sum(float(s.get("estimated_duration_sec") or 5.0) for s in scenes)
                brief = _json.loads((d / "brief.json").read_text(encoding="utf-8")) if (d / "brief.json").is_file() else {}
                title = brief.get("title") or d.name
                stamp = time.strftime("%d/%m %H:%M", time.localtime(d.stat().st_mtime))
                self.project_list.insert("", END, iid=str(d), values=(
                    title, len(scenes), f"{dur:.1f}s", stamp))
        except Exception:
            pass

    def open_project_from_list(self, _event):
        chosen = self.project_list.selection()
        if not chosen:
            return
        proj_dir = chosen[0]
        try:
            self.show_preview(proj_dir)
        except Exception as exc:
            messagebox.showerror("Không mở được preview", str(exc))

    def use_library(self):
        from core.util import safe_name
        topic = self.media_query.get().strip()
        folder = ROOT / "downloads" / safe_name(topic, 40) if topic else ROOT / "downloads"
        self.assembly.folder.set(str(folder if folder.is_dir() else ROOT / "downloads"))
        self.sections.select(self.creation_tab)
        self.creation_pages.select(self.script_host)
        self.assembly.scan()

    def show_preview(self, project_dir):
        if self.preview and not self.preview.can_leave():
            return
        if self.preview:
            self.preview._on_close()
        for widget in self.preview_host.winfo_children():
            widget.destroy()
        self.preview = PreviewWindow(self.preview_host, str(project_dir), embedded=True)
        self.sections.select(self.creation_tab)
        self.creation_pages.select(self.preview_host)

    def close_app(self):
        if self.assembly.busy:
            return messagebox.showinfo("Đang chuẩn bị hồ sơ", "Chờ đọc kho / đóng gói hoàn tất rồi đóng app để không bỏ dở thao tác.")
        if self.preview and not self.preview.can_leave():
            return
        if self.preview:
            self.preview._on_close()
        self.root.destroy()

    def start(self): self.root.mainloop()


from ui_preview_tools import PreviewTools


class PreviewWindow(PreviewTools):
    """Cửa sổ xem trước timeline kiểu CapCut: asset nối tiếp chiếu liên tục,
    kịch bản/phụ đề chạy bên dưới, chưa render thật.
    """

    def __init__(self, parent, project_dir: str, embedded: bool = False):
        self.parent = parent
        try:
            import sys as _s
            _s.path.insert(0, str(ROOT))
            from brain.preview import build_timeline, load_project, timeline_summary
            self._build_timeline = build_timeline
            self._load_project = load_project
            self._timeline_summary = timeline_summary
        except Exception as exc:
            raise RuntimeError(f"Không tải được brain.preview: {exc}")

        self.project_dir = Path(project_dir)
        self.proj = self._load_project(self.project_dir)
        # scenes là nguồn sự thật để chỉnh sửa & lưu lại
        self.scenes: list[dict] = self.proj["scenes"]
        self.assets: dict[str, dict] = self.proj["assets"]
        self.timeline = self._rebuild_timeline()
        if not self.timeline:
            raise RuntimeError("Project không có cảnh nào để xem trước.")

        self.embedded = embedded
        if embedded:
            self.win = ttk.Frame(parent)
            self.win.pack(fill=BOTH, expand=True)
        else:
            self.win = tk.Toplevel(parent)
            self.win.title(f"Timeline Preview — {self.project_dir.name}")
            self.win.geometry("1280x820")
            self.win.minsize(1000, 640)
            self.win.configure(bg=C["bg"])
            self.win.protocol("WM_DELETE_WINDOW", self._request_close)
        self._dirty = False
        self._saved_scene_json = json.dumps(self.scenes, ensure_ascii=False, sort_keys=True)
        self._rendered_path = None
        self._render_busy = False
        self._closed = False
        self._render_cancel = threading.Event()
        from brain.local_audio import LocalAudio
        self._native_audio = LocalAudio(self.project_dir / ".preview_cache" / "audio")

        self.play_idx = 0
        self.play_t = 0.0
        self.playing = False
        self.after_id = None
        self._photo = None
        self._vid_frame = 0
        self._vid_reader = None
        self._vid_meta = None
        self._vid_source = None
        self._audio_proc = None
        self._suppress_seek = False
        self._drag = None          # trạng thái kéo-thả timeline: None | ("move", idx, start_x) | ("resize", idx)
        self._tl_items = {}        # idx -> id của clip rect trên canvas
        self._resize_id = None

        self._build_ui()
        self._show_scene(0)

    # ---------------- dựng lại timeline từ scenes đã chỉnh ----------------
    def _rebuild_timeline(self) -> list[dict]:
        self.proj["scenes"] = self.scenes
        tl = self._build_timeline(self.proj)
        # gắn lại media vào từng scene theo asset_ids đã chọn (đã có trong timeline)
        return tl

    def _reload_summary(self):
        self._sum = self._timeline_summary(self.timeline)

    def _refresh_all(self, keep_idx: int | None = None):
        """Dựng lại timeline + clip bar + seek + summary sau khi chỉnh sửa."""
        self.pause()
        self._dirty = True
        self._rendered_path = None
        old_idx = self.play_idx if keep_idx is None else keep_idx
        self.timeline = self._rebuild_timeline()
        self._reload_summary()
        self.reload_captions()
        self.scale.configure(to=max(1.0, self._sum["total_duration_sec"]))
        self._render_clip_bar()
        if self.timeline:
            self._show_scene(min(old_idx, len(self.timeline) - 1), persist_notes=False)
        self._update_summary_label()
    def _build_ui(self):
        w = self.win
        head = ttk.Frame(w, style="Panel.TFrame", padding=12); head.pack(fill=X)
        ttk.Label(head, text="Preview local · bản mẫu trước khi edit trên Kaggle", style="Sub.TLabel").pack(anchor="w")
        brief = self.proj.get("brief", {})
        title = brief.get("title") or self.project_dir.name
        self._sum = self._timeline_summary(self.timeline)
        self.summary_lbl = ttk.Label(head, text="", style="Sub.TLabel")
        self.summary_lbl.pack(anchor="w", pady=(2, 0))
        self._update_summary_label()

        panes = ttk.Panedwindow(w, orient=tk.HORIZONTAL)
        panes.pack(fill=BOTH, expand=True, padx=12, pady=8)
        player = ttk.Frame(panes)
        inspector_outer = ttk.Frame(panes, width=390)
        panes.add(player, weight=4)
        panes.add(inspector_outer, weight=2)
        self.inspector_tabs = ttk.Notebook(inspector_outer)
        self.inspector_tabs.pack(fill=BOTH, expand=True)
        captions_tab = ttk.Frame(self.inspector_tabs, padding=8)
        edit_tab = ttk.Frame(self.inspector_tabs)
        effects_tab = ttk.Frame(self.inspector_tabs, padding=8)
        audio_tab = ttk.Frame(self.inspector_tabs, padding=8)
        for pane, title in [(captions_tab, "Phụ đề"), (edit_tab, "Cảnh"), (effects_tab, "Hồ sơ"), (audio_tab, "TTS mẫu")]:
            self.inspector_tabs.add(pane, text=title)
        def scroll_content(host):
            surface = Canvas(host, bg=C['bg'], highlightthickness=0, width=350)
            bar = ttk.Scrollbar(host, orient='vertical', command=surface.yview)
            surface.configure(yscrollcommand=bar.set)
            bar.pack(side=RIGHT, fill=Y); surface.pack(side=LEFT, fill=BOTH, expand=True)
            content = ttk.Frame(surface)
            item = surface.create_window(0, 0, window=content, anchor='nw')
            content.bind('<Configure>', lambda e: surface.configure(scrollregion=surface.bbox('all')))
            surface.bind('<Configure>', lambda e: surface.itemconfigure(item, width=e.width))
            return content
        effects_tab = scroll_content(effects_tab)
        audio_tab = scroll_content(audio_tab)
        inspector_scroll = Canvas(edit_tab, bg=C["bg"], highlightthickness=0, width=360)
        inspector_bar = ttk.Scrollbar(edit_tab, orient="vertical", command=inspector_scroll.yview)
        inspector_scroll.configure(yscrollcommand=inspector_bar.set)
        inspector_bar.pack(side=RIGHT, fill=Y)
        inspector_scroll.pack(side=LEFT, fill=BOTH, expand=True)
        inspector = ttk.Frame(inspector_scroll)
        inspector_item = inspector_scroll.create_window(0, 0, window=inspector, anchor="nw")
        inspector.bind("<Configure>", lambda _e: inspector_scroll.configure(scrollregion=inspector_scroll.bbox("all")))
        inspector_scroll.bind("<Configure>", lambda e: inspector_scroll.itemconfigure(inspector_item, width=e.width))
        ttk.Label(player, text="PREVIEW · phụ đề mềm · audio tham chiếu", style="Sub.TLabel").pack(anchor="w", pady=6)
        self.canvas = Canvas(player, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=True, padx=12, pady=(0, 8))
        self.canvas.bind("<Configure>", self._resize_preview)
        self.build_caption_tools(captions_tab)
        self.build_audio_tools(audio_tab)

        # thanh tiến trình
        prog = ttk.Frame(player, padding=(12, 0, 12, 4)); prog.pack(fill=X)
        self.scale = ttk.Scale(prog, from_=0.0, to=max(1.0, self._sum["total_duration_sec"]),
                               command=self._on_seek)
        self.scale.pack(side=LEFT, fill=X, expand=True)
        self.tlbl = ttk.Label(prog, text="00:00.0 / 00:00.0", style="Muted.TLabel", width=20)
        self.tlbl.pack(side=RIGHT)

        # kịch bản / phụ đề chạy dưới
        sub = ttk.Frame(inspector, style="Panel.TFrame", padding=12); sub.pack(fill=X, pady=(0, 8))
        self.subtitle = ttk.Label(sub, text="", style="Sub.TLabel", wraplength=330, justify="left")
        self.subtitle.pack(fill=X)
        self.scene_info = ttk.Label(sub, text="", style="Sub.TLabel", wraplength=350, justify="left")
        self.scene_info.pack(fill=X, pady=(4, 0))

        # nút điều khiển
        ctrl = ttk.Frame(player, padding=12); ctrl.pack(fill=X)
        self.btn_play = ttk.Button(ctrl, text="▶ Phát", style="Accent.TButton", command=self.toggle_play)
        self.btn_play.pack(side=LEFT, padx=(0, 6))
        ttk.Button(ctrl, text="⏮ Cảnh trước", style="Ghost.TButton",
                   command=lambda: self._jump(-1)).pack(side=LEFT, padx=(0, 6))
        ttk.Button(ctrl, text="⏭ Cảnh sau", style="Ghost.TButton",
                   command=lambda: self._jump(1)).pack(side=LEFT)

        # ---------- timeline kéo-thả thật (kiểu CapCut) ----------
        tl_box = ttk.LabelFrame(player, text="  Timeline — kéo cảnh / kéo mép đổi thời lượng  ", padding=8)
        tl_box.pack(fill=X, padx=12, pady=(0, 8))
        self.tl_canvas = Canvas(tl_box, height=56, bg=C["panel"], highlightthickness=0)
        self.tl_canvas.pack(fill=X)
        self.tl_canvas.bind("<Button-1>", self._tl_press)
        self.tl_canvas.bind("<B1-Motion>", self._tl_drag)
        self.tl_canvas.bind("<ButtonRelease-1>", self._tl_release)
        self.tl_canvas.bind("<Configure>", lambda _e: self._render_clip_bar())
        self._render_clip_bar()

        # ---------- toolbar chỉnh sửa (kiểu CapCut) ----------
        edit = ttk.LabelFrame(inspector, text="  Cảnh đang chọn  ", padding=10); edit.pack(fill=X, pady=(0, 8))
        r1 = ttk.Frame(edit); r1.pack(fill=X)
        ttk.Label(r1, text="Thời lượng (giây):").pack(side=LEFT)
        self.dur_var = StringVar(value="5.0")
        ttk.Entry(r1, textvariable=self.dur_var, width=8).pack(side=LEFT, padx=(6, 14))
        ttk.Button(r1, text="⏱ Áp dụng", style="Ghost.TButton", command=self.apply_duration).pack(side=LEFT, padx=(0, 14))

        speed_row = ttk.Frame(edit); speed_row.pack(fill=X, pady=6)
        ttk.Label(speed_row, text="Tốc độ video:").pack(side=LEFT)
        self.speed_var = StringVar(value="1.0")
        ttk.Combobox(speed_row, textvariable=self.speed_var, width=6, state="readonly",
                     values=["0.5", "0.75", "1.0", "1.25", "1.5", "2.0"]).pack(side=LEFT, padx=(6, 14))
        ttk.Button(speed_row, text="Áp dụng", style="Ghost.TButton", command=self.apply_speed).pack(side=LEFT)

        r2 = ttk.Frame(edit); r2.pack(fill=X, pady=(8, 0))
        ttk.Button(r2, text="🖼 Đổi asset", style="Ghost.TButton", command=self.change_asset).pack(side=LEFT, padx=(0, 6))
        ttk.Button(r2, text="✂ Cắt bỏ cảnh", style="Warn.TButton", command=self.cut_scene).pack(side=LEFT, padx=(0, 6))
        r3 = ttk.Frame(edit); r3.pack(fill=X, pady=6)
        ttk.Button(r3, text="⬅ Lùi", style="Ghost.TButton", command=lambda: self.move_scene(-1)).pack(side=LEFT, padx=(0, 6))
        ttk.Button(r3, text="➡ Tiến", style="Ghost.TButton", command=lambda: self.move_scene(1)).pack(side=LEFT)
        effects = ttk.LabelFrame(effects_tab, text="  Hướng dựng / bàn giao  ", padding=10)
        effects.pack(fill=BOTH, expand=True)
        ttk.Label(effects, text="Chữ trên hình:").pack(anchor="w")
        self.title_var = StringVar()
        ttk.Entry(effects, textvariable=self.title_var).pack(fill=X, pady=4)
        self.effect_var = StringVar(value="fade")
        ttk.Combobox(effects, textvariable=self.effect_var, state="readonly",
                     values=["fade", "slide", "pop", "typewriter"]).pack(fill=X)
        ttk.Label(effects, text="Ghi chú hướng dựng (lưu vào profile):").pack(anchor="w", pady=(8, 4))
        self.note_var = StringVar()
        ttk.Entry(effects, textvariable=self.note_var).pack(fill=X)
        ttk.Button(effects, text="Áp dụng chữ / ghi chú cho cảnh", command=self.apply_notes).pack(fill=X, pady=6)
        ttk.Label(effects, text="Dựng preview để xem hiệu ứng ngay bên trái. Sửa cảnh sẽ trở về xem nhanh cho đến lần dựng mới.",
                  wraplength=350, style="Muted.TLabel").pack(fill=X)
        ttk.Button(effects, text="Lưu profile nháp + bản sao", style="Green.TButton", command=self.save_scenes).pack(fill=X, pady=(12, 4))
        self.render_button = ttk.Button(effects, text="Dựng preview hiệu ứng ngay trong app", style="Accent.TButton", command=self.open_remotion)
        self.render_button.pack(fill=X, pady=4)
        ttk.Button(effects, text="Duyệt hướng dựng cho Kaggle", command=self.approve_profile).pack(fill=X, pady=4)
        ttk.Button(effects, text="Xuất gói ZIP cho Kaggle", command=self.export_kaggle).pack(fill=X)
        ttk.Button(effects, text="Flow3 • Tài nguyên / SFX / gói Studio", command=self.open_studio_handoff).pack(fill=X, pady=4)
        self.render_status = ttk.Label(effects, text="Remotion / FFmpeg chạy nền trên máy này.", wraplength=350, style="Muted.TLabel")
        self.render_status.pack(fill=X, pady=4)
        ttk.Button(effects, text="Hủy dựng preview", command=self._render_cancel.set).pack(fill=X)
        self.win.after(100, lambda: self._show_scene(self.play_idx))
        self.win.after_idle(lambda: panes.sashpos(0, max(580, self.win.winfo_width() - 400)))

    def _update_summary_label(self):
        s = self._sum
        brief = self.proj.get("brief", {})
        title = brief.get("title") or self.project_dir.name
        self.summary_lbl.configure(text=(
            f"{title}  ·  {s['scenes']} cảnh  ·  {s['total_duration_sec']}s  ·  "
            f"{s['with_media']} có ảnh/video  ·  {s['with_audio']} có audio  ·  "
            f"{s['with_subtitle']} có phụ đề  ·  {s.get('asset_warnings', 0)} asset cần xem lại"
        ))

    # ---------------- chỉnh sửa ----------------
    def apply_duration(self):
        self._store_notes()
        try:
            d = float(self.dur_var.get())
        except ValueError:
            return messagebox.showwarning("Sai số", "Thời lượng phải là số, ví dụ 5.0")
        import math
        if not math.isfinite(d) or d <= 0.1:
            return messagebox.showwarning("Sai số", "Thời lượng phải > 0.1 giây")
        sc = self.scenes[self.play_idx]
        sc["estimated_duration_sec"] = d
        self._refresh_all()

    def apply_speed(self):
        self._store_notes()
        try:
            sp = float(self.speed_var.get())
        except ValueError:
            return
        sc = self.scenes[self.play_idx]
        # tốc độ >1 = nhanh = thời lượng giảm; <1 = chậm = thời lượng tăng
        base = float(sc.get("estimated_duration_sec") or 5.0) * float(sc.get("playback_rate", 1))
        sc["playback_rate"] = sp
        sc["estimated_duration_sec"] = round(base / sp, 2)
        self._refresh_all()

    def change_asset(self):
        self._store_notes()
        sc = self.scenes[self.play_idx]
        # liệt kê asset có sẵn
        if not self.assets:
            return messagebox.showinfo("Không có asset", "Project không có asset nào trong assets.jsonl.")
        ids = list(self.assets.keys())
        chosen = simpledialog.askstring(
            "Đổi asset", "asset_id có sẵn:\n" + ", ".join(ids) + "\n\nChọn asset_id:",
            initialvalue=(sc.get("asset_ids") or [""])[0])
        if not chosen:
            return
        if chosen not in self.assets:
            return messagebox.showwarning("Không có", f"'{chosen}' không trong danh sách asset.")
        sc["asset_ids"] = [chosen]
        sc["status"] = "ready"
        self._refresh_all()

    def cut_scene(self):
        self._store_notes()
        if len(self.scenes) <= 1:
            return messagebox.showwarning("Không thể cắt", "Phải giữ ít nhất 1 cảnh.")
        if not messagebox.askyesno("Cắt bỏ", "Xoá cảnh đang chọn khỏi timeline?"):
            return
        del self.scenes[self.play_idx]
        self._refresh_all(keep_idx=min(self.play_idx, len(self.scenes) - 1))

    def move_scene(self, delta: int):
        self._store_notes()
        i = self.play_idx
        j = i + delta
        if 0 <= j < len(self.scenes):
            self.scenes[i], self.scenes[j] = self.scenes[j], self.scenes[i]
            self._refresh_all(keep_idx=j)

    def save_scenes(self):
        from brain.profile import save_profile
        try:
            self.apply_notes()
            profile = save_profile(self.project_dir, self.scenes)
            self._mark_saved()
            messagebox.showinfo("Đã lưu", f"Profile nháp r{profile['revision']}; bản cũ nằm trong revisions/.\nTTS là mẫu, Kaggle cần dựng giọng cuối.")
            return True
        except Exception as exc:
            messagebox.showerror("Không lưu được", str(exc))
            return False

    def apply_notes(self):
        if self._store_notes():
            self._refresh_all()

    def _store_notes(self):
        if not hasattr(self, "title_var") or not 0 <= self.play_idx < len(self.scenes):
            return False
        updates = dict(on_screen_text=self.title_var.get(), text_effect=self.effect_var.get(), review_notes=self.note_var.get())
        if any(self.scenes[self.play_idx].get(k, "fade" if k == "text_effect" else "") != v for k, v in updates.items()):
            self.scenes[self.play_idx].update(updates)
            self._dirty = True
            self._rendered_path = None
            return True
        return False

    def open_remotion(self):
        from brain.profile import save_profile
        from brain.remotion_bridge import render_preview
        from queue import Queue, Empty
        if self._render_busy:
            return messagebox.showinfo("Đang dựng", "Chờ preview hiện tại hoặc bấm Hủy dựng preview.")
        try:
            self.pause()
            self.apply_notes()
            save_profile(self.project_dir, self.scenes)
            self._mark_saved()
        except Exception as exc:
            return messagebox.showerror("Remotion", str(exc))
        snapshot = json.dumps(self.scenes, sort_keys=True, ensure_ascii=False)
        self._render_busy = True
        self._render_cancel.clear()
        self.render_button.configure(state="disabled")
        queue = Queue()
        started = time.monotonic()
        def worker():
            try: queue.put((True, render_preview(self.project_dir, self._render_cancel)))
            except Exception as exc: queue.put((False, str(exc)))
        def poll():
            if self._closed: return
            try: ok, value = queue.get_nowait()
            except Empty:
                self.render_status.configure(text=f"Remotion đang dựng local… {int(time.monotonic()-started)}s. Bạn vẫn có thể thao tác app.")
                self.win.after(200, poll); return
            self._render_busy = False
            self.render_button.configure(state="normal")
            if not ok:
                self.render_status.configure(text="Dựng chưa hoàn tất.")
                messagebox.showerror("Preview", value); return
            if snapshot != json.dumps(self.scenes, sort_keys=True, ensure_ascii=False):
                self.render_status.configure(text="Cảnh đã đổi trong khi dựng. Bấm Dựng preview lại để xem bản mới."); return
            self.pause()
            self._rendered_path = str(value)
            self.render_status.configure(text="Đã dựng hiệu ứng · bấm Phát để xem/nghe ngay trong app.")
            self._show_scene(0)
        threading.Thread(target=worker, daemon=True).start()
        self.win.after(100, poll)

    def _mark_saved(self):
        self._saved_scene_json = json.dumps(self.scenes, ensure_ascii=False, sort_keys=True)
        self._dirty = False

    def _has_changes(self):
        import copy
        scenes = copy.deepcopy(self.scenes)
        updates = dict(on_screen_text=self.title_var.get(), text_effect=self.effect_var.get(), review_notes=self.note_var.get())
        for key, value in updates.items():
            if scenes[self.play_idx].get(key, "fade" if key == "text_effect" else "") != value:
                scenes[self.play_idx][key] = value
        return json.dumps(scenes, ensure_ascii=False, sort_keys=True) != self._saved_scene_json

    def can_leave(self):
        if self._render_busy and not messagebox.askyesno("Đang dựng preview", "Hủy tác vụ render đang chạy để rời dự án?"):
            return False
        if self._has_changes():
            answer = messagebox.askyesnocancel("Chưa lưu", "Lưu thay đổi thành profile nháp trước khi rời dự án?")
            if answer is None: return False
            if answer and not self.save_scenes(): return False
        return True

    def _request_close(self):
        if self.can_leave(): self._on_close()

    def open_studio_handoff(self):
        if self._render_busy:
            return messagebox.showinfo("Đang dựng", "Chờ hoặc hủy render trước khi bàn giao.")
        if self._has_changes() or not (self.project_dir / "preview_profile.json").exists():
            if not self.save_scenes():
                return
        from ui_studio_handoff import StudioHandoff
        existing = getattr(self, "_studio_handoff", None)
        if existing is not None and existing.win.winfo_exists():
            existing.win.lift()
            return
        self._studio_handoff = StudioHandoff(self.win, self.project_dir)

    def export_kaggle(self):
        from brain.assembly import export_package
        from brain.profile import save_profile
        if self._render_busy:
            return messagebox.showinfo("Đang dựng", "Chờ hoặc hủy render trước khi xuất gói.")
        path = filedialog.asksaveasfilename(initialfile=self.project_dir.name + ".zip", defaultextension=".zip", filetypes=[("Gói Kaggle", "*.zip")])
        if not path: return
        try:
            if self._has_changes() or not (self.project_dir / "preview_profile.json").exists():
                self.apply_notes()
                save_profile(self.project_dir, self.scenes)
                self._mark_saved()
            export_package(self.project_dir, path)
            profile = json.loads((self.project_dir / "preview_profile.json").read_text(encoding="utf-8"))
            messagebox.showinfo("Đã xuất ZIP", f"{path}\nTrạng thái duyệt: {profile['review_status']}. Thiếu asset: {len(profile['missing_assets'])}.\nKaggle nhận profile + media + audio mẫu; chưa tự chạy renderer Kaggle.")
        except Exception as exc:
            messagebox.showerror("Xuất hồ sơ", str(exc))

    def _resize_preview(self, _event):
        if self._resize_id:
            self.win.after_cancel(self._resize_id)
        self._resize_id = self.win.after(150, self._redraw_preview)

    def _redraw_preview(self):
        self._resize_id = None
        if self._vid_reader is not None:
            self._show_video_frame()
        else:
            self._load_media(self.timeline[self.play_idx])
        self.update_caption_overlay()

    def approve_profile(self):
        from brain.profile import save_profile
        if not messagebox.askyesno("Duyệt hướng dựng", "Duyệt hướng hiện tại? Audio vẫn là mẫu; máy Kaggle phải tạo giọng/render cuối."):
            return
        try:
            self.apply_notes()
            profile = save_profile(self.project_dir, self.scenes, approved=True)
            self._mark_saved()
            messagebox.showinfo("Hồ sơ đã duyệt", f"{self.project_dir / 'preview_profile.json'}\nCòn thiếu asset: {len(profile['missing_assets'])}.\nChuyển cả thư mục project sang Kaggle, không chỉ file JSON.")
        except Exception as exc:
            messagebox.showerror("Hồ sơ", str(exc))

    def _render_clip_bar(self):
        """Vẽ timeline kéo-thả trên canvas: mỗi clip rộng theo thời lượng."""
        cv = self.tl_canvas
        cv.delete("all")
        self._tl_items = {}
        w = cv.winfo_width() or 800
        if not self.timeline:
            return
        total = max(0.001, self._sum["total_duration_sec"])
        pad_x, pad_y, gap = 8, 6, 3
        usable = max(10, w - 2 * pad_x)
        h = 56 - 2 * pad_y
        for i, c in enumerate(self.timeline):
            x0 = pad_x + (c["start"] / total) * usable
            x1 = pad_x + (c["end"] / total) * usable
            if x1 - x0 < 14:  # clip quá ngắn vẫn vẽ đủ rộng để nhìn/bấm
                x1 = x0 + 14
            selected = (i == self.play_idx)
            color = C["accent"] if c["media"] else (C["amber"] if c["status"] == "needs_ai_gen" else C["muted"])
            outline = "#ffffff" if selected else C["border"]
            rect = cv.create_rectangle(x0, pad_y, x1, pad_y + h, fill=color,
                                       outline=outline, width=2 if selected else 1)
            cv.create_text((x0 + x1) / 2, pad_y + h / 2, text=str(i + 1),
                           fill="#ffffff", font=("Segoe UI", 9, "bold"))
            # mép phải để resize (vùng nhạy)
            cv.create_rectangle(x1 - 4, pad_y, x1 + 4, pad_y + h, fill="", outline="",
                                tags=("resize", str(i)))
            self._tl_items[i] = (rect, x0, x1, pad_y, pad_y + h)

    # ---------------- timeline drag & drop ----------------
    def _tl_hit(self, event):
        """Trả (loại, idx) nếu click trúng clip (move) hoặc mép phải (resize)."""
        for i, (rect, x0, x1, y0, y1) in self._tl_items.items():
            if y0 <= event.y <= y1:
                if x1 - 5 <= event.x <= x1 + 5:
                    return ("resize", i)
                if x0 <= event.x <= x1:
                    return ("move", i)
        return (None, None)

    def _tl_press(self, event):
        kind, idx = self._tl_hit(event)
        if kind is None:
            return
        self._show_scene(idx)
        if kind == "resize":
            self._drag = ("resize", idx, event.x, float(self.scenes[idx].get("estimated_duration_sec") or 5.0))
        else:
            self._drag = ("move", idx, event.x)

    def _tl_drag(self, event):
        if not self._drag:
            return
        self._store_notes()
        kind = self._drag[0]
        if kind == "move":
            _, idx, start_x = self._drag
            # quy đổi dx -> số vị trí đã vượt qua (mỗi clip ~ chiều rộng trung bình)
            cv = self.tl_canvas
            w = cv.winfo_width() or 800
            total = max(0.001, self._sum["total_duration_sec"])
            pad_x, gap = 8, 3
            usable = max(10, w - 2 * pad_x)
            if len(self.timeline) > 1:
                avg = usable / len(self.timeline)
                if avg <= 0:
                    return
                delta = int(round((event.x - start_x) / avg))
                j = idx + delta
                if j != idx and 0 <= j < len(self.scenes):
                    self.scenes[idx], self.scenes[j] = self.scenes[j], self.scenes[idx]
                    self._drag = ("move", j, event.x)
                    self._refresh_all(keep_idx=j)
        else:  # resize
            _, idx, start_x, base_dur = self._drag
            cv = self.tl_canvas
            w = cv.winfo_width() or 800
            total = max(0.001, self._sum["total_duration_sec"])
            pad_x = 8
            usable = max(10, w - 2 * pad_x)
            px_per_sec = usable / total
            if px_per_sec <= 0:
                return
            new_dur = base_dur + (event.x - start_x) / px_per_sec
            new_dur = max(0.2, round(new_dur, 1))
            self.scenes[idx]["estimated_duration_sec"] = new_dur
            self._refresh_all(keep_idx=idx)

    def _tl_release(self, _event):
        self._drag = None

    # ---------------- play logic ----------------
    def toggle_play(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if self.playing:
            return
        if self.play_idx == len(self.timeline) - 1 and self.play_t >= self.timeline[-1]['duration']:
            self._show_scene(0)
        self.playing = True
        self._last_tick = time.monotonic()
        self._start_audio(self.timeline[self.play_idx])
        self.btn_play.configure(text="⏸ Tạm dừng")
        self._tick()

    def pause(self):
        self.playing = False
        if self.after_id:
            self.win.after_cancel(self.after_id)
            self.after_id = None
        self.btn_play.configure(text="▶ Phát")
        self._stop_audio()

    def _jump(self, delta: int):
        ni = max(0, min(len(self.timeline) - 1, self.play_idx + delta))
        self._show_scene(ni)

    def _on_seek(self, val):
        if self._suppress_seek:
            return
        try:
            t = float(val)
        except (TypeError, ValueError):
            return
        # tìm cảnh chứa thời điểm t
        for i, c in enumerate(self.timeline):
            if c["start"] <= t < c["end"]:
                self._show_scene(i, offset=t - c["start"])
                return
        last = self.timeline[-1]
        self._show_scene(len(self.timeline) - 1, offset=last['duration'])

    def _show_scene(self, idx: int, offset: float = 0.0, persist_notes: bool = True):
        # Keep typed notes when navigating instead of silently discarding them.
        if persist_notes and idx != self.play_idx:
            if self._store_notes():
                self.timeline = self._rebuild_timeline()
        idx = max(0, min(len(self.timeline) - 1, idx))
        self.play_idx = idx
        self.play_t = offset
        self._last_tick = time.monotonic()
        c = self.timeline[idx]
        if hasattr(self, "title_var"):
            self.title_var.set(self.scenes[idx].get("on_screen_text", ""))
            self.effect_var.set(self.scenes[idx].get("text_effect", "fade"))
            self.note_var.set(self.scenes[idx].get("review_notes", ""))
            self.speed_var.set(str(self.scenes[idx].get("playback_rate", 1.0)))
        # đồng bộ ô thời lượng/tốc độ với cảnh đang chọn
        if hasattr(self, "dur_var"):
            self.dur_var.set(str(float(c.get("duration", 5.0))))
        self._render_clip_bar()
        # cập nhật phụ đề + info
        sub_text = c["subtitle"] or ""
        if c["on_screen_text"]:
            sub_text = (c["on_screen_text"] + "\n" + sub_text).strip()
        self.subtitle.configure(text=(sub_text[:220] + '…' if len(sub_text) > 220 else sub_text) or "Không có lời")
        warning = "\n⚠ " + " ".join(c.get("visual_warnings", [])) if c.get("visual_warnings") else ""
        self.scene_info.configure(text=(
            f"Cảnh {idx + 1}/{len(self.timeline)} · {c['scene_id']} · "
            f"{c['start']:.1f}s–{c['end']:.1f}s · status={c['status']} · "
            f"visual: {c['visual_intent'] or '—'}{warning}"
        ))
        self._load_media(c)
        self._last_tick = time.monotonic()
        # khởi động audio nếu đang phát
        if self.playing:
            self._start_audio(c)
        self._update_tlbl()

    def _load_media(self, c: dict):
        media = self._rendered_path or c.get("media", "")
        if not media:
            self.canvas.delete("all")
            self._photo = None
            self._img_loaded = {"idx": -1, "photo": None, "kind": None}
            self._release_reader()
            self.canvas.create_text(420, 240, text="（chưa có asset cho cảnh này）",
                                    fill="#8b90a0", font=("Segoe UI", 13))
            return
        ext = Path(media).suffix.lower()
        try:
            if ext in (".mp4", ".mov", ".webm", ".mkv", ".avi"):
                self._load_video(c, media)
            else:
                self._load_image(c, media)
        except Exception as exc:
            self.canvas.delete("all")
            self.canvas.create_text(420, 240, text=f"Lỗi tải asset: {exc}",
                                    fill=C["red"], font=("Segoe UI", 11))

    def _load_image(self, c: dict, media: str):
        from PIL import Image, ImageTk
        self._release_reader()
        img = Image.open(media)
        w = self.canvas.winfo_width() or 840
        h = self.canvas.winfo_height() or 420
        img.thumbnail((w, h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(w // 2, h // 2, image=self._photo, anchor="center")
        warnings = c.get("visual_warnings", [])
        if warnings:
            message = "⚠ ASSET NGUỒN CẦN XEM LẠI\n" + " ".join(warnings)
            self.canvas.create_rectangle(12, 12, max(280, w - 12), 82,
                                         fill="#31131a", outline="#ef4444", width=2)
            self.canvas.create_text(26, 25, text=message, anchor="nw", width=max(240, w - 52),
                                    fill="#fecaca", font=("Segoe UI", 11, "bold"))

    def _load_video(self, c: dict, media: str):
        import imageio.v2 as iio
        if self._vid_reader is None or self._vid_source != media:
            self._release_reader()
            self._vid_reader = iio.get_reader(media)
            self._vid_meta = self._vid_reader.get_meta_data()
            self._vid_source = media
        sc = self.scenes[self.play_idx]
        source_time = c["start"] + self.play_t if self._rendered_path else float(sc.get("trim_in", 0)) + self.play_t * float(sc.get("playback_rate", 1))
        self._vid_frame = int(source_time * (self._vid_meta.get("fps") or 24))
        self._show_video_frame()

    def _release_reader(self):
        if self._vid_reader is not None:
            try:
                self._vid_reader.close()
            except Exception:
                pass
            self._vid_reader = None
            self._vid_meta = None
            self._vid_source = None

    def _show_video_frame(self):
        if self._vid_reader is None:
            return
        try:
            frame = self._vid_reader.get_data(self._vid_frame)
        except Exception:
            return  # giữ frame cuối, không lặp video ngoài ý muốn
        from PIL import Image, ImageTk
        import numpy as np
        img = Image.fromarray(np.asarray(frame))
        w = self.canvas.winfo_width() or 840
        h = self.canvas.winfo_height() or 420
        img.thumbnail((w, h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(w // 2, h // 2, image=self._photo, anchor="center")

    def _start_audio(self, c: dict):
        self._stop_audio()
        a = self._rendered_path if self._rendered_path and any(s.get("audio") for s in self.timeline) else c.get("audio", "")
        if a and Path(a).exists():
            offset = c["start"] + self.play_t if self._rendered_path else self.play_t
            self._native_audio.play(a, offset, duration=c["duration"] - self.play_t)

    def _stop_audio(self):
        self._native_audio.stop()
        if self._audio_proc and self._audio_proc.poll() is None:
            try:
                self._audio_proc.terminate()
            except Exception:
                pass
        self._audio_proc = None

    def _tick(self):
        if not self.playing:
            return
        c = self.timeline[self.play_idx]
        now = time.monotonic()
        self.play_t += now - self._last_tick
        self._last_tick = now
        if self._native_audio.error:
            self.render_status.configure(text=self._native_audio.error)
        # nếu là video: nạp frame kế tiếp
        if self._vid_reader is not None:
            fps = (self._vid_meta or {}).get("fps", 0) or 24
            sc = self.scenes[self.play_idx]
            source_time = c["start"] + self.play_t if self._rendered_path else float(sc.get("trim_in", 0)) + self.play_t * float(sc.get("playback_rate", 1))
            self._vid_frame = int(source_time * fps)
            self._show_video_frame()

        if self.play_t >= c["duration"]:
            # qua cảnh kế
            if self.play_idx + 1 < len(self.timeline):
                remaining = self.play_t - c['duration']
                next_idx = self.play_idx + 1
                while next_idx < len(self.timeline) - 1 and remaining >= self.timeline[next_idx]['duration']:
                    remaining -= self.timeline[next_idx]['duration']
                    next_idx += 1
                self._show_scene(next_idx, offset=min(remaining, self.timeline[next_idx]['duration']))
            else:
                self.play_t = c['duration']
                self.pause()
                self._update_tlbl()
                return
        self._update_tlbl()
        self.after_id = self.win.after(50, self._tick)

    def _update_tlbl(self):
        c = self.timeline[self.play_idx]
        cur = c["start"] + self.play_t
        self.update_caption_overlay()
        total = self._sum["total_duration_sec"]
        self.tlbl.configure(text=f"{cur:06.1f}s / {total:06.1f}s")
        self._suppress_seek = True
        try:
            self.scale.set(cur)
        finally:
            self._suppress_seek = False

    def _on_close(self):
        self._closed = True
        self._render_cancel.set()
        self.pause()
        self._native_audio.close()
        if self._resize_id:
            self.win.after_cancel(self._resize_id)
        self._release_reader()
        self.win.destroy()


if __name__ == "__main__":
    PipelineApp().start()
