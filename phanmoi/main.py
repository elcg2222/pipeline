#!/usr/bin/env python3
"""
CLI của crawler-tool.

    python main.py search "ocean" --mode image --commercial-only
    python main.py search "AI agent" --mode news_fast
    python main.py crawl news --fulltext
    python main.py stats
    python main.py health
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
from models import Doc
from router import Router
from storage import Store


# ---------------- lệnh ----------------

async def cmd_search(args) -> None:
    adapters = config.build_adapters(include_news=args.mode in ("news", "news_fast", "all"))
    router = Router(adapters, deadline_sec=config.DEADLINE_SEC)

    print(f"Tìm '{args.query}' | mode={args.mode} | {len(router.adapters)} nguồn...\n")
    docs = await router.search(
        args.query, mode=args.mode, limit=args.limit,
        commercial_only=args.commercial_only,
    )

    if args.save:
        store = Store(config.DB_PATH)
        new, dup = store.upsert_many(docs)
        store.close()
        print(f"[kho] thêm mới {new}, đã có {dup}\n")

    if args.json:
        print(json.dumps([d.to_dict() for d in docs], ensure_ascii=False, indent=2))
    else:
        _print_docs(docs)


async def cmd_crawl(args) -> None:
    """Ingest Loop: kéo nội dung mới theo lịch và nhét vào kho."""
    from adapters.rss_news import load_feeds

    if args.what != "news":
        print("v0 mới hỗ trợ: crawl news")
        return

    feeds = load_feeds(config.FEEDS_PATH, fetch_fulltext=args.fulltext)
    if not feeds:
        print(f"Không tìm thấy feed nào trong {config.FEEDS_PATH}")
        return

    store = Store(config.DB_PATH)
    total_new = total_dup = 0

    async def one(f):
        nonlocal total_new, total_dup
        try:
            docs, _ = await f.poll()
            n, d = store.upsert_many(docs)
            total_new += n
            total_dup += d
            print(f"  {f.name:<28} +{n:<4} (trùng {d})")
        except Exception as e:
            print(f"  {f.name:<28} LỖI: {type(e).__name__}: {e}")

    print(f"Kéo {len(feeds)} feed"
          f"{' (kèm full text, sẽ chậm)' if args.fulltext else ''}...\n")
    sem = asyncio.Semaphore(8)

    async def guarded(f):
        async with sem:
            await one(f)

    await asyncio.gather(*(guarded(f) for f in feeds))
    print(f"\nTổng: +{total_new} bài mới, {total_dup} trùng")
    print(f"Kho hiện có {store.stats()['total']} bản ghi")
    store.close()


async def cmd_local(args) -> None:
    """Tìm trong kho đã cào, không gọi mạng."""
    store = Store(config.DB_PATH)
    docs = store.search(
        args.query, source_type=args.type,
        commercial_only=args.commercial_only, limit=args.limit,
    )
    store.close()
    _print_docs(docs)


async def cmd_stats(args) -> None:
    store = Store(config.DB_PATH)
    s = store.stats()
    store.close()
    print(f"Tổng bản ghi: {s['total']}\n")
    print(f"{'Nguồn':<22}{'Loại':<12}{'Số lượng':>10}{'Thương mại OK':>16}")
    print("-" * 60)
    for r in s["by_source"]:
        print(f"{r['source_name']:<22}{r['source_type']:<12}"
              f"{r['n']:>10}{r['comm'] or 0:>16}")


async def cmd_health(args) -> None:
    adapters = config.build_adapters()
    print("Kiểm tra sức khoẻ adapter:\n")
    for a in adapters:
        if not a.enabled:
            print(f"  {a.name:<28} TẮT (thiếu API key)")
            continue
        ok = await a.health()
        print(f"  {a.name:<28} {'OK' if ok else 'HỎNG'}")


# ---------------- hiển thị ----------------

def _print_docs(docs: list[Doc]) -> None:
    if not docs:
        print("Không có kết quả.")
        return
    for i, d in enumerate(docs, 1):
        lic = d.license
        if lic.commercial_use is True:
            mark = "[TM OK]"
        elif lic.commercial_use is False:
            mark = "[cấm TM]"
        else:
            mark = "[? chưa rõ]"
        print(f"{i:>2}. {d.title[:72]}")
        print(f"    {d.source_name} | {d.source_type} | điểm {d.score:.2f} | {mark} {lic.id}")
        if d.published_at:
            print(f"    đăng: {d.published_at}")
        print(f"    {d.source_url}")
        if d.media_url:
            print(f"    media: {d.media_url}")
        print()


# ---------------- entrypoint ----------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="crawler-tool", description="Thu thập đa nguồn")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="tìm trực tiếp từ các nguồn (có gọi mạng)")
    s.add_argument("query")
    s.add_argument("--mode", default="all",
                   choices=["all", "image", "video", "news", "news_fast"])
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--commercial-only", action="store_true",
                   help="chỉ lấy nội dung đã xác minh được dùng thương mại")
    s.add_argument("--save", action="store_true", help="lưu kết quả vào kho")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)

    c = sub.add_parser("crawl", help="kéo nội dung mới vào kho (Ingest Loop)")
    c.add_argument("what", choices=["news"])
    c.add_argument("--fulltext", action="store_true",
                   help="tải toàn văn bài báo bằng trafilatura (chậm)")
    c.set_defaults(func=cmd_crawl)

    l = sub.add_parser("local", help="tìm trong kho đã cào, không gọi mạng")
    l.add_argument("query")
    l.add_argument("--type", default=None)
    l.add_argument("--limit", type=int, default=20)
    l.add_argument("--commercial-only", action="store_true")
    l.set_defaults(func=cmd_local)

    st = sub.add_parser("stats", help="thống kê kho")
    st.set_defaults(func=cmd_stats)

    h = sub.add_parser("health", help="kiểm tra adapter nào còn sống")
    h.set_defaults(func=cmd_health)
    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        asyncio.run(args.func(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
