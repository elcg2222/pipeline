"""Cầu nối PC <-> AutoDub (Kaggle/Colab).

Đây là mắt xích V1 chưa có: máy bạn ở Windows, AutoDub chạy GPU trên cloud.
Không thể gọi hàm trực tiếp, nên dùng Google Drive làm hàng đợi chung:

    PC  --rclone copy-->  Drive/autodub/inbox/<batch>/  (video + jobs.jsonl)
    Kaggle notebook đọc inbox, xử lý, ghi ra Drive/autodub/outbox/<batch>/
    PC  --rclone copy-->  local outputs/dubbed/  và cập nhật state = dubbed

Ưu điểm: bất đồng bộ hoàn toàn, mất mạng giữa chừng chạy lại không sao,
và notebook chỉ cần biết đúng 1 file jobs.jsonl.
"""
from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from core.store import Store
from core.util import run_cmd, safe_name, which

log = logging.getLogger("stage.bridge")


def _job(row) -> dict:
    """Manifest mà AutoDub Flow 1 sẽ đọc. Truyền sẵn context để AI dịch đúng giọng."""
    return {
        "uid": row["uid"],
        "file": Path(row["local_path"]).name,
        "platform": row["platform"],
        "topic": row["topic"],
        "source_url": row["url"],
        "original_title": row["title"],
        "duration": row["duration"],
        "score": row["score"],
        # gợi ý cho Flow 2 (dịch) - càng nhiều ngữ cảnh, bản dịch càng tự nhiên
        "target_lang": "vi",
        "style": "review bán hàng, ngắn gọn, xưng 'mình', gọi người xem là 'bạn'",
        "keep_bgm": True,
        "burn_subtitle": False,
    }


def export(store: Store, cfg: dict, limit: int = 20) -> dict:
    b = cfg.get("bridge", {})
    staging = Path(b.get("staging_dir", "outputs/to_autodub"))
    batch = datetime.now().strftime("batch_%Y%m%d_%H%M")
    out = staging / batch
    out.mkdir(parents=True, exist_ok=True)

    rows = [r for r in store.pick("downloaded", limit=limit)
            if r["last_error"] == "qc_passed" or not b.get("require_qc", True)]
    if not rows:
        log.info("Không có video nào đã qua QC để xuất.")
        shutil.rmtree(out, ignore_errors=True)
        return {"exported": 0}

    jobs = []
    for r in rows:
        src = Path(r["local_path"])
        if not src.exists():
            continue
        shutil.copy2(src, out / src.name)
        jobs.append(_job(r))

    (out / "jobs.jsonl").write_text(
        "\n".join(json.dumps(j, ensure_ascii=False) for j in jobs),
        encoding="utf-8")

    # đẩy lên Drive
    remote = b.get("rclone_remote")
    if remote and which("rclone"):
        code, _, err = run_cmd(
            ["rclone", "copy", str(out), f"{remote}/inbox/{batch}",
             "--transfers", "4", "--progress"], timeout=b.get("upload_timeout", 3600))
        if code != 0:
            log.error("rclone upload lỗi: %s", err[:300])
            return {"exported": 0, "error": err[:300]}
        log.info("Đã upload %d video lên %s/inbox/%s", len(jobs), remote, batch)
    else:
        log.warning("Chưa cấu hình rclone. File nằm ở %s, hãy upload thủ công.", out)

    for j in jobs:
        store.set_state(j["uid"], "exported", last_error=batch)

    return {"exported": len(jobs), "batch": batch, "dir": str(out)}


def collect(store: Store, cfg: dict) -> dict:
    """Kéo video đã lồng tiếng từ Drive/outbox về máy và đánh dấu 'dubbed'."""
    b = cfg.get("bridge", {})
    remote = b.get("rclone_remote")
    local = Path(b.get("dubbed_dir", "outputs/dubbed"))
    local.mkdir(parents=True, exist_ok=True)

    if not (remote and which("rclone")):
        log.error("Cần rclone + bridge.rclone_remote để thu kết quả.")
        return {}

    code, _, err = run_cmd(["rclone", "copy", f"{remote}/outbox", str(local),
                            "--transfers", "4", "--progress"],
                           timeout=b.get("upload_timeout", 3600))
    if code != 0:
        log.error("rclone download lỗi: %s", err[:300])
        return {}

    done = 0
    for manifest in local.rglob("results.jsonl"):
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                res = json.loads(line)
            except json.JSONDecodeError:
                continue
            uid, outfile = res.get("uid"), res.get("output_file")
            if not uid:
                continue
            p = manifest.parent / (outfile or "")
            if res.get("status") == "ok" and p.exists():
                store.set_state(uid, "dubbed", local_path=str(p))
                done += 1
            else:
                store.set_state(uid, "error", last_error=str(res.get("error"))[:300])
    log.info("Đã thu về %d video hoàn thiện.", done)
    return {"dubbed": done}
