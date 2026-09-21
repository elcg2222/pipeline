#!/usr/bin/env python
"""Cửa sổ desktop cục bộ cho Social Trend Pipeline.

Chạy: python desktop_app.py
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
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Tk, StringVar, Text
from tkinter import messagebox, ttk

DEFAULT_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
ROOT = Path(os.environ.get("PIPELINE_HOME", DEFAULT_ROOT)).resolve()
DB = ROOT / "data" / "pipeline.db"


class PipelineApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("Social Trend Pipeline")
        self.root.geometry("1180x720")
        self.root.minsize(900, 560)
        self.proc: subprocess.Popen | None = None
        self.output = ""
        self.status = StringVar(value="Sẵn sàng")
        self.summary = StringVar(value="Đang đọc dữ liệu…")
        self._build()
        self.refresh()

    def _build(self):
        root = self.root
        style = ttk.Style(root)
        try: style.theme_use("clam")
        except Exception: pass
        outer = ttk.Frame(root, padding=16); outer.pack(fill=BOTH, expand=True)
        ttk.Label(outer, text="Social Trend Pipeline", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Ứng dụng chỉ chạy trong máy này — không mở web server.").pack(anchor="w", pady=(2, 12))
        ttk.Label(outer, textvariable=self.summary, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))

        actions = ttk.Frame(outer); actions.pack(fill=X, pady=(0, 10))
        for label, command in [("Quét nguồn", "discover"), ("Tải video", "download"),
                               ("QC", "qc"), ("Chạy toàn bộ", "all"),
                               ("Xét lại rejected", "recheck"), ("Thử lại", "retry")]:
            ttk.Button(actions, text=label, command=lambda c=command: self.run(c)).pack(side=LEFT, padx=(0, 7))

        add = ttk.LabelFrame(outer, text="Thêm video từ URL công khai", padding=10); add.pack(fill=X, pady=(0, 10))
        ttk.Label(add, text="Facebook · Instagram · Reddit · Discord attachment/CDN · TikTok · YouTube · web khác. Mỗi dòng một link, tối đa 20.").pack(anchor="w")
        self.urls = Text(add, height=3, font=("Consolas", 10)); self.urls.pack(fill=X, pady=7)
        ttk.Button(add, text="Nhận diện và thêm vào hàng đợi", command=self.add_urls).pack(anchor="w")

        body = ttk.PanedWindow(outer, orient="vertical"); body.pack(fill=BOTH, expand=True)
        table_box = ttk.Frame(body, padding=3); body.add(table_box, weight=4)
        cols = ("platform", "title", "state", "attempts", "error", "updated")
        self.tree = ttk.Treeview(table_box, columns=cols, show="headings")
        for col, label, width in [("platform", "Nguồn", 90), ("title", "Video", 310), ("state", "Trạng thái", 100),
                                  ("attempts", "Lần thử", 65), ("error", "Lỗi gần nhất", 360), ("updated", "Cập nhật", 135)]:
            self.tree.heading(col, text=label); self.tree.column(col, width=width, stretch=col in {"title", "error"})
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview); scroll.pack(side=RIGHT, fill=Y)
        self.tree.configure(yscrollcommand=scroll.set); self.tree.bind("<Double-1>", self.open_source)

        logbox = ttk.LabelFrame(body, text="Tác vụ gần nhất", padding=5); body.add(logbox, weight=1)
        self.log = Text(logbox, height=7, state="disabled", font=("Consolas", 9)); self.log.pack(fill=BOTH, expand=True)
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(8, 0))

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
            for r in rows:
                stamp = time.strftime("%d/%m %H:%M", time.localtime(r["updated_at"] or 0)) if r["updated_at"] else "—"
                self.tree.insert("", END, iid=r["uid"], values=(r["platform"], r["title"] or r["uid"], r["state"], r["attempts"], (r["last_error"] or "").replace("\n", " ")[:200], stamp), tags=(r["url"],))
            if self.proc and self.proc.poll() is not None:
                self.output += self.proc.stdout.read() if self.proc.stdout else ""
                self.proc = None; self.status.set("Hoàn tất — dữ liệu đã được làm mới")
            self._set_log(self.output[-8000:])
        except Exception as exc:
            self.status.set(f"Không thể đọc dữ liệu: {exc}")
        self.root.after(2000, self.refresh)

    def _set_log(self, text: str):
        self.log.configure(state="normal"); self.log.delete("1.0", END); self.log.insert("1.0", text); self.log.configure(state="disabled")

    def run(self, command: str, urls: list[str] | None = None):
        if self.proc and self.proc.poll() is None:
            return messagebox.showwarning("Pipeline đang chạy", "Hãy chờ tác vụ hiện tại hoàn tất.")
        python = sys.executable if not getattr(sys, "frozen", False) else ("python.exe" if os.name == "nt" else "python3")
        args = [python, "run.py", command]
        for url in urls or []: args += ["--url", url]
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.proc = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", creationflags=flags)
            self.output = ""; self.status.set(f"Đang chạy: {command}")
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
        self.urls.delete("1.0", END); self.run("add", urls)

    def open_source(self, _event):
        chosen = self.tree.selection()
        if chosen:
            webbrowser.open(self.tree.item(chosen[0], "tags")[0])

    def start(self): self.root.mainloop()


if __name__ == "__main__":
    PipelineApp().start()
