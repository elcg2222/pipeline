"""Cầu nối đa định dạng: ảnh thương mại + tin tức/tài liệu + video stock.

Bọc lại bộ `phanmoi` (Router + Adapter + SQLite FTS5) thành các hàm đồng bộ
để pipeline chính (`run.py`) và app UI (`desktop_app.py`) gọi được mà không
phải import asyncio rải rác.

Các mode:
    image     — ảnh thương mại (Openverse/Pexels/Pixabay)
    video     — video stock (Pexels) + video social (đã có ở providers)
    news      — tin tức/bài báo (RSS + trafilatura full-text)
    all       — gộp mọi nguồn trên

Tải file: ảnh -> .jpg/.png, video stock -> .mp4, tin -> .md (toàn văn).
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from core.util import safe_name

ROOT = Path(__file__).resolve().parent
PHANMOI = ROOT / "phanmoi"

# Đưa phanmoi vào sys.path để import config/router/storage/models
for _p in (str(PHANMOI), str(PHANMOI / "adapters")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MODE_LABELS = {
    "image": "Ảnh thương mại",
    "video": "Video stock",
    "news": "Tin tức / tài liệu",
    "all": "Tổng hợp",
}

# Phần mở rộng theo loại nội dung khi tải file
_EXT = {
    "image": ".jpg",
    "video": ".mp4",
    "news": ".md",
}

_CONTENT_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "video/mp4": ".mp4", "video/webm": ".webm",
    "video/quicktime": ".mov",
}


def _adapter_docs(docs) -> list[dict]:
    """Chuẩn hoá Doc (phanmoi) thành dict gọn cho pipeline/UI."""
    out = []
    for d in docs:
        out.append({
            "id": d.id,
            "type": d.source_type,
            "source": d.source_name,
            "title": d.title or "",
            "content": d.content or "",
            "url": d.source_url,
            "media_url": d.media_url,
            "thumbnail_url": d.thumbnail_url,
            "author": d.author,
            "published_at": d.published_at,
            "score": round(d.score, 3),
            "commercial_use": d.license.commercial_use,
            "attribution_required": d.license.attribution_required,
            "attribution_text": d.license.attribution_text,
            "tags": d.tags or [],
            "width": d.width,
            "height": d.height,
        })
    return out


def search(query: str, mode: str = "all", limit: int = 20,
           commercial_only: bool = False) -> dict:
    """Tìm nội dung theo chủ đề trên nhiều nguồn. Trả dict {mode, docs, count}."""
    import config as phanmoi_config
    from router import Router

    mode = mode if mode in MODE_LABELS else "all"

    async def _run():
        adapters = phanmoi_config.build_adapters(
            include_news=mode in ("news", "news_fast", "all")
        )
        router = Router(adapters, deadline_sec=phanmoi_config.DEADLINE_SEC)
        docs = await router.search(query, mode=mode, limit=limit,
                                   commercial_only=commercial_only)
        relevant = [a for a in adapters if mode == "all" or
                    a.source_type == ("news" if mode == "news_fast" else mode)]
        return docs, {
            "enabled": [a.name for a in relevant if a.enabled],
            "disabled": [a.name for a in relevant if not a.enabled],
        }

    docs, sources = asyncio.run(_run())
    return {
        "mode": mode,
        "mode_label": MODE_LABELS.get(mode, mode),
        "count": len(docs),
        "docs": _adapter_docs(docs),
        "sources": sources,
    }


def crawl_news(fulltext: bool = False) -> dict:
    """Ingest Loop: kéo tin mới từ RSS vào kho lưu trữ."""
    import config as phanmoi_config
    from storage import Store

    def _run():
        from adapters.rss_news import load_feeds
        feeds = load_feeds(phanmoi_config.FEEDS_PATH, fetch_fulltext=fulltext)
        store = Store(phanmoi_config.DB_PATH)
        total_new = total_dup = 0
        per_source = []

        async def one(f):
            nonlocal total_new, total_dup
            try:
                docs, _ = await f.poll()
                n, d = store.upsert_many(docs)
                total_new += n
                total_dup += d
                per_source.append({"source": f.name, "new": n, "dup": d})
            except Exception as e:
                per_source.append({"source": f.name, "error": str(e)})

        async def all_feeds():
            await asyncio.gather(*(one(f) for f in feeds))

        asyncio.run(all_feeds())
        total = store.stats()["total"]
        store.close()
        return total_new, total_dup, total, per_source

    new, dup, total, per_source = _run()
    return {"new": new, "dup": dup, "total": total, "per_source": per_source}


def archive_search(query: str, source_type: str | None = None,
                   limit: int = 20, commercial_only: bool = False) -> dict:
    """Tìm trong kho đã cào (nhanh, không gọi mạng)."""
    import config as phanmoi_config
    from storage import Store

    store = Store(phanmoi_config.DB_PATH)
    docs = store.search(query, source_type=source_type,
                        commercial_only=commercial_only, limit=limit)
    store.close()
    return {"count": len(docs), "docs": _adapter_docs(docs)}


def archive_stats() -> dict:
    import config as phanmoi_config
    from storage import Store
    store = Store(phanmoi_config.DB_PATH)
    s = store.stats()
    store.close()
    return s


def download(docs: list[dict], topic: str, download_dir: str = "downloads",
             max_per_type: int = 0, allow_restricted: bool = False,
             workers: int = 6, retries: int = 3) -> dict:
    """Tải song song, atomically và lưu manifest giấy phép cạnh media."""
    base = Path(download_dir) / safe_name(topic or "misc", 40)
    done = {"image": 0, "video": 0, "news": 0}
    failed: list[dict] = []
    skipped: list[dict] = []
    manifest_rows: list[dict] = []
    per_type_budget: dict[str, int] = {}
    selected: list[dict] = []

    for doc in docs:
        d_type = doc.get("type") or "image"
        if max_per_type and per_type_budget.get(d_type, 0) >= max_per_type:
            continue
        if doc.get("commercial_use") is False and not allow_restricted:
            skipped.append({"title": doc.get("title", ""), "reason": "restricted_license"})
            continue
        if d_type != "news" and not doc.get("media_url"):
            skipped.append({"title": doc.get("title", ""), "reason": "missing_media_url"})
            continue
        per_type_budget[d_type] = per_type_budget.get(d_type, 0) + 1
        selected.append(doc)

    media_docs: list[dict] = []
    for doc in selected:
        if (doc.get("type") or "image") == "news":
            try:
                dest = _save_news(base, doc)
                done["news"] += 1
                manifest_rows.append(_manifest_row(doc, dest))
            except Exception as exc:
                failed.append({"title": doc.get("title", ""), "error": str(exc)[:200]})
        else:
            media_docs.append(doc)

    with ThreadPoolExecutor(max_workers=max(1, min(workers, 12))) as pool:
        futures = {pool.submit(_download_media, base, doc, retries): doc for doc in media_docs}
        for future in as_completed(futures):
            doc = futures[future]
            try:
                dest = future.result()
                d_type = doc.get("type") or "image"
                done[d_type] = done.get(d_type, 0) + 1
                manifest_rows.append(_manifest_row(doc, dest))
            except Exception as exc:
                failed.append({"title": doc.get("title", ""), "error": str(exc)[:200]})

    base.mkdir(parents=True, exist_ok=True)
    manifest = base / "manifest.jsonl"
    known: set[str | None] = set()
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            try:
                known.add(json.loads(line).get("id"))
            except (json.JSONDecodeError, AttributeError):
                continue
    new_rows = [row for row in manifest_rows if row.get("id") not in known]
    if new_rows:
        with manifest.open("a", encoding="utf-8") as fh:
            for row in new_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {"downloaded": done, "failed": failed, "skipped": skipped,
            "manifest": str(manifest), "dir": str(base)}


def _download_media(base: Path, doc: dict, retries: int) -> Path:
    """Tải qua file .part, retry có backoff và xác minh ảnh trước khi nhận."""
    import httpx

    url = doc["media_url"]
    d_type = doc.get("type") or "image"
    stem = safe_name(f"{doc.get('id', '')}_{doc.get('title', '')}"[:70], 70)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 Chrome/125 Safari/537.36"}
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        part: Path | None = None
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60,
                              headers=headers) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                ext = (_CONTENT_EXT.get(content_type) or
                       Path(urlparse(url).path).suffix.lower() or
                       mimetypes.guess_extension(content_type) or _EXT.get(d_type, ".bin"))
                if len(ext) > 6 or not ext.startswith("."):
                    ext = _EXT.get(d_type, ".bin")
                dest = base / d_type / f"{stem}{ext}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and dest.stat().st_size > 0:
                    return dest
                part = dest.with_suffix(dest.suffix + ".part")
                with part.open("wb") as fh:
                    for chunk in response.iter_bytes(1024 * 256):
                        fh.write(chunk)
            if not part.exists() or part.stat().st_size < 1024:
                raise ValueError("file tải về quá nhỏ")
            if d_type == "image":
                from PIL import Image
                with Image.open(part) as image:
                    image.verify()
            part.replace(dest)
            return dest
        except Exception as exc:
            last_error = exc
            if part is not None:
                part.unlink(missing_ok=True)
            if attempt + 1 < max(1, retries):
                time.sleep(2 ** attempt)
    raise RuntimeError(str(last_error) if last_error else "download failed")


def _manifest_row(doc: dict, dest: Path) -> dict:
    return {
        "id": doc.get("id"), "type": doc.get("type"), "source": doc.get("source"),
        "title": doc.get("title"), "source_url": doc.get("url"),
        "media_url": doc.get("media_url"), "local_path": str(dest),
        "commercial_use": doc.get("commercial_use"),
        "attribution_required": doc.get("attribution_required"),
        "attribution_text": doc.get("attribution_text"),
        "downloaded_at": time.time(),
    }


def _save_news(base: Path, doc: dict) -> Path:
    d = base / "news"
    d.mkdir(parents=True, exist_ok=True)
    stem = safe_name(f"{doc.get('source', '')}_{doc.get('title', '')}"[:70], 70)
    dest = d / f"{stem}.md"
    if dest.exists():
        return dest
    lines = [
        f"# {doc.get('title', '')}",
        "",
        f"- Nguồn: {doc.get('source', '')}",
        f"- Tác giả: {doc.get('author') or '—'}",
        f"- Đăng: {doc.get('published_at') or '—'}",
        f"- Link gốc: {doc.get('url', '')}",
        f"- Dùng thương mại: {doc.get('commercial_use')}",
        f"- Yêu cầu ghi nguồn: {doc.get('attribution_required')}",
        "",
        "---",
        "",
        doc.get("content", "") or "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


if __name__ == "__main__":
    # Tự kiểm tra nhanh
    print(json.dumps(search("AI", mode="news", limit=3), ensure_ascii=False, indent=2))
