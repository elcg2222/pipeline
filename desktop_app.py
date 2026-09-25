#!/usr/bin/env python
"""Cửa sổ desktop cục bộ cho Social Trend Pipeline.

Chạy: python desktop_app.py  (hoặc double-click "Pipeline App.vbs" / start_desktop_app.bat)
Không mở trình duyệt và không lắng nghe cổng mạng.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Tk, StringVar, Text, BooleanVar
from tkinter import messagebox, ttk

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
        self.output = ""
        self.status = StringVar(value="Đang kiểm tra công cụ…")
        self.summary = StringVar(value="Đang đọc dữ liệu…")
        self.style = _apply_style(self.root)
        self._build()
        self.refresh()
        self.root.after(400, self._startup_check)

    def _build(self):
        root = self.root
        outer = ttk.Frame(root, padding=16); outer.pack(fill=BOTH, expand=True)

        # ---------- Header ----------
        head = ttk.Frame(outer, style="Panel.TFrame", padding=16); head.pack(fill=X, pady=(0, 12))
        ttk.Label(head, text="🎬  Social Trend Pipeline", style="Title.TLabel").pack(anchor="w")
        ttk.Label(head, text="Video · Ảnh thương mại · Tin tức — chạy hoàn toàn trên máy này",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 8))
        ttk.Label(head, textvariable=self.summary, style="Summary.TLabel").pack(anchor="w")

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
        statusbar = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 6)); statusbar.pack(fill=X, pady=(10, 0))
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
                self.output += self.proc.stdout.read() if self.proc.stdout else ""
                self.proc = None; self.status.set("✅ Hoàn tất — dữ liệu đã được làm mới")
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

    def start(self): self.root.mainloop()


if __name__ == "__main__":
    PipelineApp().start()
