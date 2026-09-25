"""Cấu hình + nơi lắp ráp adapter. Thêm nguồn mới thì sửa build_adapters()."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = os.getenv("CRAWLER_DB", str(ROOT / "data" / "crawler.db"))
FEEDS_PATH = os.getenv("CRAWLER_FEEDS", str(ROOT / "feeds.txt"))
DEADLINE_SEC = float(os.getenv("CRAWLER_DEADLINE", "8"))


def _load_dotenv() -> None:
    """Đọc .env đơn giản, không cần thêm thư viện."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

PEXELS_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
OPENVERSE_KEY = os.getenv("OPENVERSE_TOKEN")     # tuỳ chọn


def build_adapters(include_news: bool = True, fulltext: bool = False) -> list:
    from adapters.pexels import PexelsAdapter, PexelsVideoAdapter
    from adapters.pixabay import PixabayAdapter
    from adapters.openverse import OpenverseAdapter
    from adapters.rss_news import load_feeds

    adapters = [
        PexelsAdapter(PEXELS_KEY),
        PexelsVideoAdapter(PEXELS_KEY),
        PixabayAdapter(PIXABAY_KEY),
        OpenverseAdapter(OPENVERSE_KEY),
    ]
    if include_news:
        adapters += load_feeds(FEEDS_PATH, fetch_fulltext=fulltext)
    return adapters
