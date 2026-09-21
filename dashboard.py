#!/usr/bin/env python
"""Dashboard local for Social Trend Pipeline.

Run: python dashboard.py
Then open http://127.0.0.1:8765
"""
from __future__ import annotations

import html
import json
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "pipeline.db"
PORT = 8765
RUNNING: dict[str, object] = {"process": None, "command": None, "started": None, "output": ""}
RUN_LOCK = threading.Lock()

PAGE = r'''<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Pipeline Dashboard</title>
<style>
:root{color-scheme:dark;--bg:#101419;--card:#19212b;--line:#2b3a48;--text:#eaf0f6;--muted:#9babb9;--blue:#65b8ff;--green:#42d392;--red:#ff7575;--yellow:#ffc857}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,Segoe UI,sans-serif}main{max-width:1500px;margin:auto;padding:26px}h1{margin:0;font-size:24px}.sub{color:var(--muted);margin:5px 0 22px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:15px}.n{font-size:26px;font-weight:700}.label{color:var(--muted);margin-top:4px}.bar,section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-top:16px}button,select,input,textarea{border:1px solid var(--line);background:#111923;color:var(--text);border-radius:7px;padding:9px 11px}button{cursor:pointer;color:white;background:#1769aa}button:hover{background:#2581ca}button:disabled{opacity:.55;cursor:wait}.actions{display:flex;gap:8px;flex-wrap:wrap}.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}input{min-width:230px}textarea{width:min(760px,100%);min-height:72px;resize:vertical;font:13px ui-monospace,Consolas,monospace}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px 8px;text-align:left;border-top:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600;border-top:0}.title{max-width:430px}.title a{color:var(--blue);text-decoration:none}.tag{display:inline-block;padding:3px 7px;border-radius:20px;background:#243443}.queued,.downloaded,.qc_passed,.exported,.dubbed,.published{color:var(--green)}.error,.qc_failed,.rejected,.duplicate{color:var(--red)}.downloading{color:var(--yellow)}.muted{color:var(--muted)}pre{white-space:pre-wrap;max-height:220px;overflow:auto;margin:10px 0 0;color:#c8d5df}.hidden{display:none}@media(max-width:750px){main{padding:14px}table{font-size:12px}.hide-sm{display:none}}
</style></head><body><main><h1>Social Trend Pipeline</h1><div class="sub">Theo dõi video được lấy từ web nào, tiến độ xử lý và lỗi gần nhất.</div>
<div class="cards" id="cards"></div>
<section><div class="actions"><button onclick="run('discover')">Quét nguồn</button><button onclick="run('download')">Tải video</button><button onclick="run('qc')">Chạy QC</button><button onclick="run('export')">Xuất AutoDub</button><button onclick="run('collect')">Thu AutoDub</button><button onclick="run('all')">Chạy toàn bộ</button><button onclick="run('recheck')">Xét lại rejected</button><button onclick="run('retry')">Cho phép thử tải lại</button></div><div style="margin:17px 0 7px"><b>Thêm video từ link</b> <span class="muted">Facebook · Instagram · Reddit · Discord attachment/CDN · TikTok · YouTube · web khác</span></div><textarea id="manualUrls" oninput="previewSources()" placeholder="Mỗi dòng một link video công khai. Có thể dán tối đa 20 link."></textarea><div class="filters" style="margin:8px 0 0"><button onclick="addUrls()">Nhận diện và thêm vào hàng đợi</button><span id="sourcePreview" class="muted"></span></div><div id="job" class="muted" style="margin-top:10px"></div><pre id="output" class="hidden"></pre></section>
<section><div class="filters"><select id="platform"><option value="">Tất cả website</option></select><select id="state"><option value="">Tất cả trạng thái</option></select><input id="search" placeholder="Tìm tiêu đề / chủ đề"><button onclick="loadVideos()">Lọc</button></div><div style="overflow:auto"><table><thead><tr><th>Website</th><th>Video</th><th class="hide-sm">Chủ đề</th><th>Điểm</th><th>Trạng thái</th><th>Lần thử / lỗi</th><th class="hide-sm">Cập nhật</th></tr></thead><tbody id="videos"></tbody></table></div></section>
<section><h3 style="margin-top:0">Lần chạy gần đây</h3><div style="overflow:auto"><table><thead><tr><th>Bước</th><th>Thời điểm</th><th>Thành công</th><th>Lỗi</th><th>Ghi chú</th></tr></thead><tbody id="runs"></tbody></table></div></section>
</main><script>
const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); const dt=t=>t?new Date(t*1000).toLocaleString('vi-VN'):'—';
async function api(path){return (await fetch(path)).json()}
async function refresh(){let d=await api('/api/summary'); let cards=Object.entries(d.states).map(([k,v])=>`<div class="card"><div class="n ${k}">${v}</div><div class="label">${esc(k)}</div></div>`).join(''); cards+=Object.entries(d.platforms).map(([k,v])=>`<div class="card"><div class="n">${v}</div><div class="label">${esc(k)}</div></div>`).join(''); document.querySelector('#cards').innerHTML=cards||'<div class="card">Chưa có dữ liệu</div>'; fill('platform',d.platforms,'Tất cả website');fill('state',d.states,'Tất cả trạng thái'); let j=d.job; document.querySelector('#job').textContent=j.command?`Đang chạy: ${j.command} từ ${dt(j.started)}`:'Không có tác vụ đang chạy';let o=document.querySelector('#output');o.textContent=j.output||'';o.className=j.output?'':'hidden';document.querySelectorAll('.actions button').forEach(b=>b.disabled=!!j.command)}
function fill(id,values,label){let x=document.getElementById(id),v=x.value;x.innerHTML=`<option value="">${label}</option>`+Object.keys(values).sort().map(k=>`<option ${k==v?'selected':''}>${esc(k)}</option>`).join('')}
async function loadVideos(){let p=new URLSearchParams({platform:platform.value,state:state.value,q:search.value});let d=await api('/api/videos?'+p);videos.innerHTML=d.rows.map(r=>`<tr><td><span class="tag">${esc(r.platform)}</span></td><td class="title"><a href="${esc(r.url)}" target="_blank" rel="noreferrer">${esc(r.title||r.native_id||r.uid)}</a><div class="muted">${esc(r.author||'')}</div></td><td class="hide-sm">${esc(r.topic||'—')}</td><td>${Number(r.score||0).toFixed(3)}</td><td class="${esc(r.state)}">${esc(r.state)}</td><td>${r.attempts||0}${r.last_error?`<div class="error">${esc(r.last_error)}</div>`:''}</td><td class="hide-sm muted">${dt(r.updated_at)}</td></tr>`).join('')||'<tr><td colspan="7" class="muted">Không có video phù hợp.</td></tr>'}
async function loadRuns(){let d=await api('/api/runs');runs.innerHTML=d.rows.map(r=>`<tr><td>${esc(r.stage)}</td><td>${dt(r.finished||r.started)}</td><td class="queued">${r.ok}</td><td class="error">${r.failed}</td><td class="muted">${esc(r.note||'')}</td></tr>`).join('')||'<tr><td colspan="5" class="muted">Chưa có lần chạy nào.</td></tr>'}
async function run(command){let r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command})});let d=await r.json();if(d.error)alert(d.error);refresh()}
function guess(url){let h;try{h=new URL(url).hostname.replace(/^www\./,'')}catch{return 'không hợp lệ'};if(/facebook\.com|fb\.watch/.test(h))return'Facebook';if(/instagram\.com|instagr\.am/.test(h))return'Instagram';if(/reddit\.com|redd\.it/.test(h))return'Reddit';if(/discord\.com|discordapp\.com|discordapp\.net/.test(h))return'Discord';if(/tiktok\.com/.test(h))return'TikTok';if(/youtube\.com|youtu\.be/.test(h))return'YouTube';return h}
function previewSources(){let urls=manualUrls.value.split(/\s+/).filter(Boolean);sourcePreview.textContent=urls.length?`Sẽ nhận diện: ${[...new Set(urls.map(guess))].join(', ')} (${urls.length} link)`:''}
async function addUrls(){let urls=manualUrls.value.split(/\s+/).filter(Boolean);if(!urls.length||urls.some(u=>!/^https?:\/\//i.test(u)))return alert('Mỗi dòng cần là URL đầy đủ, bắt đầu bằng https://');let r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'add',urls})});let d=await r.json();if(d.error)alert(d.error);else{manualUrls.value='';previewSources()}refresh()}
async function all(){await refresh();await loadVideos();await loadRuns()} all();setInterval(all,2000);
</script></body></html>'''

def query(sql: str, args=()):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()

def start_job(command: str, urls: list[str] | None = None) -> str | None:
    if command not in {"discover", "download", "qc", "export", "collect", "all", "recheck", "retry", "add"}:
        return "Lệnh không hợp lệ."
    urls = urls or []
    if command == "add" and (not urls or len(urls) > 20 or any(not u.startswith(("http://", "https://")) for u in urls)):
        return "Hãy nhập từ 1 đến 20 URL hợp lệ."
    with RUN_LOCK:
        if RUNNING["process"] is not None:
            return "Một tác vụ khác đang chạy. Hãy chờ tác vụ đó kết thúc."
        args = [sys.executable, "run.py", command]
        for url in urls if command == "add" else []:
            args += ["--url", url]
        proc = subprocess.Popen(args, cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        RUNNING.update(process=proc, command=command, started=time.time(), output="")
    def watch():
        output, _ = proc.communicate()
        with RUN_LOCK:
            RUNNING["output"] = output[-12000:]
            RUNNING["process"] = None
            RUNNING["command"] = None
    threading.Thread(target=watch, daemon=True).start()
    return None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def reply(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        parsed, params = urlparse(self.path), parse_qs(urlparse(self.path).query)
        if parsed.path == "/":
            body = PAGE.encode("utf-8"); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if not DB.exists(): return self.reply({"error": f"Không tìm thấy database: {DB}"}, 404)
        if parsed.path == "/api/summary":
            states = {r["state"]: r["count"] for r in query("SELECT state, COUNT(*) count FROM videos GROUP BY state")}
            platforms = {r["platform"]: r["count"] for r in query("SELECT platform, COUNT(*) count FROM videos GROUP BY platform")}
            with RUN_LOCK: job = {"command": RUNNING["command"], "started": RUNNING["started"], "output": RUNNING["output"]}
            return self.reply({"states": states, "platforms": platforms, "job": job})
        if parsed.path == "/api/videos":
            clauses, args = [], []
            for field in ("platform", "state"):
                value = params.get(field, [""])[0].strip()
                if value: clauses.append(f"{field}=?"); args.append(value)
            value = params.get("q", [""])[0].strip()
            if value: clauses.append("(title LIKE ? OR topic LIKE ? OR author LIKE ?)"); args += [f"%{value}%"] * 3
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            return self.reply({"rows": query("SELECT uid,platform,url,native_id,title,author,topic,score,state,attempts,last_error,updated_at FROM videos" + where + " ORDER BY updated_at DESC LIMIT 300", args)})
        if parsed.path == "/api/runs": return self.reply({"rows": query("SELECT stage,started,finished,ok,failed,note FROM runs ORDER BY id DESC LIMIT 20")})
        return self.reply({"error": "Không tìm thấy"}, 404)
    def do_POST(self):
        if self.path != "/api/run": return self.reply({"error": "Không tìm thấy"}, 404)
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            command = data["command"]
            urls = data.get("urls") or ([data["url"]] if data.get("url") else [])
            if not isinstance(urls, list) or not all(isinstance(url, str) for url in urls):
                raise ValueError("urls không hợp lệ")
        except Exception: return self.reply({"error": "Dữ liệu không hợp lệ"}, 400)
        error = start_job(command, urls)
        return self.reply({"ok": not error, "error": error}, 409 if error else 202)

if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}"
    print(f"Dashboard: {url} (press Ctrl+C to stop)")
    webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
