#!/usr/bin/env python
"""Social Trend Pipeline v2 - CLI duy nhất cho toàn bộ pipeline.

    python run.py doctor                  # kiểm tra môi trường trước khi chạy
    python run.py discover                # quét tất cả từ khoá trong config
    python run.py discover -t "máy massage cổ" -t "đèn ngủ"
    python run.py download --limit 10
    python run.py qc
    python run.py export                  # đẩy sang AutoDub
    python run.py collect                 # thu video đã lồng tiếng về
    python run.py all                     # discover -> download -> qc -> export
    python run.py status
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from core.store import Store                       # noqa: E402
from core.util import setup_logging, which         # noqa: E402

import providers.douyin_tiktok  # noqa: F401,E402  (đăng ký provider)
import providers.marketplace    # noqa: F401,E402
import providers.social_discovery  # noqa: F401,E402
import providers.discord_provider  # noqa: F401,E402


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        import yaml
        return yaml.safe_load(text)
    import json
    return json.loads(text)


def cmd_doctor(cfg, store, args):
    from providers.base import build
    print("=== MÔI TRƯỜNG ===")
    for tool, hint in [
        ("ffmpeg", "winget install Gyan.FFmpeg"),
        ("ffprobe", "đi kèm ffmpeg"),
        ("yt-dlp", "pip install -U yt-dlp"),
        ("opencli", "npm i -g @jackwener/opencli"),
        ("f2", "pip install -U f2"),
        ("rclone", "winget install Rclone.Rclone"),
    ]:
        found = which(tool)
        print(f"  {'[OK] ' if found else '[--] '}{tool:<10} {found or hint}")

    print("\n=== THƯ VIỆN PYTHON ===")
    for mod, hint in [("requests", "pip install requests"),
                      ("yaml", "pip install pyyaml"),
                      ("PIL", "pip install pillow"),
                      ("imagehash", "pip install imagehash")]:
        try:
            __import__(mod)
            print(f"  [OK] {mod}")
        except ImportError:
            print(f"  [--] {mod:<12} {hint}")

    print("\n=== PROVIDERS ===")
    for name, on in cfg.get("enabled_providers", {}).items():
        if not on:
            print(f"  [off] {name}")
            continue
        try:
            ok, why = build(name, cfg).available()
            print(f"  {'[OK] ' if ok else '[!!] '}{name:<9} {why}")
        except Exception as e:
            print(f"  [!!] {name:<9} {e}")

    print("\n=== DATABASE ===")
    print(f"  {store.path}  ->  {store.stats() or 'trống'}")


def cmd_discover(cfg, store, args):
    from stages import discover
    discover.run(store, cfg, args.topic or None)


def cmd_download(cfg, store, args):
    from stages import download
    download.run(store, cfg, args.limit)


def cmd_qc(cfg, store, args):
    from stages import qc
    qc.run(store, cfg, args.limit)


def cmd_export(cfg, store, args):
    from stages import bridge_autodub
    print(bridge_autodub.export(store, cfg, args.limit))


def cmd_collect(cfg, store, args):
    from stages import bridge_autodub
    print(bridge_autodub.collect(store, cfg))


def cmd_all(cfg, store, args):
    from stages import bridge_autodub, discover, download, qc
    discover.run(store, cfg, args.topic or None)
    download.run(store, cfg, args.limit)
    qc.run(store, cfg, args.limit * 2)
    if cfg.get("bridge", {}).get("auto_export", False):
        print(bridge_autodub.export(store, cfg, args.limit))


def cmd_status(cfg, store, args):
    stats = store.stats()
    order = ["discovered", "queued", "downloading", "downloaded", "qc_passed", "exported",
             "dubbed", "published", "qc_failed", "duplicate", "rejected", "error"]
    print("TRẠNG THÁI PIPELINE")
    for s in order:
        if s in stats:
            print(f"  {s:<13} {stats[s]:>6}")
    rows = store.conn.execute(
        "SELECT title, platform, score, state FROM videos "
        "WHERE state IN ('queued','downloaded') ORDER BY score DESC LIMIT 10").fetchall()
    if rows:
        print("\nTOP ĐANG CHỜ")
        for r in rows:
            print(f"  {r['score']:.3f} [{r['platform']:<8}] {r['state']:<11} {(r['title'] or '')[:55]}")


def cmd_add(cfg, store, args):
    from stages import import_urls
    if not args.url:
        raise ValueError("Cần ít nhất một --url")
    print(import_urls.run(store, cfg, args.url))


def cmd_recheck(cfg, store, args):
    """Đánh giá lại video bị loại theo cấu hình lọc hiện tại."""
    import time
    from core.schema import VideoItem
    from core.scoring import hard_filter, score
    started = time.time()
    queued = still_rejected = 0
    rows = store.conn.execute("SELECT * FROM videos WHERE state='rejected'").fetchall()
    for r in rows:
        item = VideoItem(platform=r["platform"], url=r["url"], native_id=r["native_id"] or "",
            title=r["title"] or "", author=r["author"] or "", author_id=r["author_id"] or "",
            views=r["views"], likes=r["likes"], comments=r["comments"], shares=r["shares"],
            collects=r["collects"], duration=r["duration"], created_at=r["created_at"],
            topic=r["topic"] or "", source=r["source"] or "")
        reason = hard_filter(item, cfg)
        if reason:
            store.set_state(item.uid, "rejected", last_error=reason)
            still_rejected += 1
        else:
            item.score, item.score_detail = score(item, cfg, store.velocity(item.uid))
            store.upsert(item)
            store.set_state(item.uid, "queued", last_error="")
            queued += 1
    store.log_run("recheck", "", started, queued, still_rejected, "đánh giá lại rejected")
    print({"queued": queued, "still_rejected": still_rejected})


def cmd_media(cfg, store, args):
    """Tìm/tải đa định dạng (ảnh, tin tức, video stock) qua phanmoi bridge."""
    import json
    import media_bridge

    if args.subcommand == "search":
        res = media_bridge.search(args.query, mode=args.type,
                                  limit=args.limit,
                                  commercial_only=args.commercial_only)
        print(f"[{res['mode_label']}] Tìm '{args.query}' -> {res['count']} kết quả\n")
        if res.get("sources", {}).get("disabled"):
            print("  Nguồn chưa cấu hình: " + ", ".join(res["sources"]["disabled"]) + "\n")
        for d in res["docs"]:
            lic = "TM-OK" if d["commercial_use"] is True else (
                "CẤM-TM" if d["commercial_use"] is False else "chưa rõ")
            media = d.get("media_url") or d.get("url") or ""
            print(f"  {d['score']:.2f} [{d['type']:<5}] [{lic:<8}] {d['title'][:60]}")
            if media:
                print(f"      {media}")
        if args.save:
            dl = media_bridge.download(res["docs"], args.query,
                                       download_dir=cfg.get("download_dir", "downloads"),
                                       max_per_type=args.max_per_type,
                                       allow_restricted=args.allow_restricted)
            print(f"\n[kho file] {json.dumps(dl['downloaded'], ensure_ascii=False)}")
            if dl.get("skipped"):
                print(f"[bỏ qua] {len(dl['skipped'])} mục (giấy phép/thiếu URL)")
            if dl.get("failed"):
                print(f"[lỗi] {len(dl['failed'])} mục")
            print(f"[manifest] {dl.get('manifest', '')}")
            print(f"[thư mục] {dl['dir']}")

    elif args.subcommand == "crawl":
        res = media_bridge.crawl_news(fulltext=args.fulltext)
        print(f"Kéo tin: +{res['new']} mới, {res['dup']} trùng, kho hiện {res['total']}")

    elif args.subcommand == "archive":
        res = media_bridge.archive_search(args.query, source_type=args.type,
                                          limit=args.limit,
                                          commercial_only=args.commercial_only)
        print(f"[kho] '{args.query}' -> {res['count']} bản ghi\n")
        for d in res["docs"]:
            print(f"  [{d['type']:<5}] {d['source']:<16} {d['title'][:60]}")

    elif args.subcommand == "stats":
        print(json.dumps(media_bridge.archive_stats(), ensure_ascii=False, indent=2))


def cmd_retry(cfg, store, args):
    """Mở lại các item đã hết lượt thử để có thể tải lại sau khi sửa cấu hình."""
    import time
    limit = cfg.get("download", {}).get("max_attempts", 3)
    cur = store.conn.execute("UPDATE videos SET attempts=0, last_error='', updated_at=? "
                             "WHERE state='queued' AND attempts>=?", (time.time(), limit))
    store.conn.commit()
    print({"reset": cur.rowcount})


COMMANDS = {
    "doctor": cmd_doctor, "discover": cmd_discover, "download": cmd_download,
    "qc": cmd_qc, "export": cmd_export, "collect": cmd_collect,
    "all": cmd_all, "status": cmd_status, "add": cmd_add, "recheck": cmd_recheck,
    "retry": cmd_retry, "media": cmd_media,
}


def main():
    ap = argparse.ArgumentParser(description="Social Trend Pipeline v2")
    ap.add_argument("command", choices=list(COMMANDS))
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("-t", "--topic", action="append", help="ghi đè từ khoá (lặp lại được)")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--log-level", default="INFO")
    ap.add_argument("--url", action="append", help="URL video công khai để thêm thủ công (dùng với add)")

    # media subcommand args
    ap.add_argument("subcommand", nargs="?", default=None,
                    help="(media) search | crawl | archive | stats")
    ap.add_argument("query", nargs="?", default=None, help="(media) từ khoá chủ đề")
    ap.add_argument("--type", default="all", help="(media) image|video|news|all")
    ap.add_argument("--commercial-only", action="store_true",
                    help="(media) chỉ lấy nội dung dùng thương mại được")
    ap.add_argument("--save", action="store_true",
                    help="(media search) tải file thật về máy")
    ap.add_argument("--max-per-type", type=int, default=0,
                    help="(media search --save) giới hạn số file mỗi loại, 0=không giới hạn")
    ap.add_argument("--allow-restricted", action="store_true",
                    help="(media search --save) cho phép lưu nội dung bị đánh dấu cấm thương mại")
    ap.add_argument("--fulltext", action="store_true",
                    help="(media crawl) bóc toàn văn bài báo")
    args = ap.parse_args()

    cfg = load_config(args.config)
    setup_logging(args.log_level, cfg.get("log_file", "logs/pipeline.log"))
    store = Store(cfg.get("db_path", "data/pipeline.db"))
    try:
        COMMANDS[args.command](cfg, store, args)
    finally:
        store.close()


if __name__ == "__main__":
    main()
