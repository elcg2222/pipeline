"""
Tin tức qua RSS + trafilatura.

Vì sao RSS chứ không crawl: RSS là kênh nhà báo chủ động đẩy ra, cập nhật
trong vài phút, không bị chặn, không cần trình duyệt. Với mục tiêu
"bản tin ra nhanh nhất trong ngày", đây là đường ngắn nhất.

trafilatura lo phần bóc nội dung chính khỏi quảng cáo/menu — tốt hơn nhiều
so với tự viết CSS selector cho từng báo.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from models import Doc, License
from .base import SourceAdapter

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import trafilatura
except ImportError:
    trafilatura = None


NEWS_LICENSE = License(
    id="copyrighted-news",
    commercial_use=False,          # nội dung báo chí có bản quyền
    modification_allowed=False,
    attribution_required=True,
)


def _to_iso(entry) -> str | None:
    tm = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not tm:
        return None
    return datetime(*tm[:6], tzinfo=timezone.utc).isoformat()


class RssNewsAdapter(SourceAdapter):
    """
    Một instance = một feed. Router sẽ tạo nhiều instance từ feeds.txt.
    """
    source_type = "news"
    capabilities = {"poll", "search"}
    requires_key = False

    def __init__(self, feed_url: str, site_name: str | None = None,
                 fetch_fulltext: bool = False) -> None:
        super().__init__(None)
        self.feed_url = feed_url
        self.name = site_name or feed_url.split("/")[2].replace("www.", "")
        self.fetch_fulltext = fetch_fulltext

    async def poll(self, cursor=None) -> tuple[list[Doc], object]:
        if feedparser is None:
            raise RuntimeError("Thiếu thư viện: pip install feedparser")

        # feedparser là đồng bộ -> đẩy sang thread để không chặn event loop
        parsed = await asyncio.to_thread(feedparser.parse, self.feed_url)

        docs: list[Doc] = []
        for e in parsed.entries:
            link = getattr(e, "link", "")
            if not link:
                continue
            summary = getattr(e, "summary", "") or ""
            docs.append(Doc(
                source_type="news",
                source_name=self.name,
                source_url=link,
                title=getattr(e, "title", ""),
                content=_strip_html(summary),
                author=getattr(e, "author", None),
                published_at=_to_iso(e),
                license=NEWS_LICENSE,
                tags=[t.get("term") for t in getattr(e, "tags", []) if t.get("term")],
            ))

        if self.fetch_fulltext:
            await self._enrich(docs)
        return docs, cursor

    async def search(self, query: str, limit: int = 20) -> list[Doc]:
        """RSS không có endpoint tìm kiếm -> lọc tại chỗ trên feed hiện tại."""
        docs, _ = await self.poll()
        q = query.lower()
        hits = [d for d in docs if q in d.title.lower() or q in d.content.lower()]
        return hits[:limit]

    async def _enrich(self, docs: list[Doc], concurrency: int = 5) -> None:
        """Tải full text. Chậm hơn nhiều -> chỉ bật khi thật cần."""
        if trafilatura is None:
            return
        sem = asyncio.Semaphore(concurrency)

        async def one(d: Doc) -> None:
            async with sem:
                try:
                    html = await asyncio.to_thread(trafilatura.fetch_url, d.source_url)
                    if not html:
                        return
                    text = await asyncio.to_thread(
                        trafilatura.extract, html, include_comments=False
                    )
                    if text:
                        d.content = text
                except Exception:
                    pass   # một bài lỗi không được làm hỏng cả mẻ

        await asyncio.gather(*(one(d) for d in docs))


def _strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s).strip()


def load_feeds(path: str | Path = "feeds.txt", fetch_fulltext: bool = False
               ) -> list[RssNewsAdapter]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("|")]
        url = parts[0]
        name = parts[1] if len(parts) > 1 else None
        out.append(RssNewsAdapter(url, name, fetch_fulltext))
    return out
