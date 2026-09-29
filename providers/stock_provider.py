"""Stock Provider cho Pexels & Pixabay API.
Tự động tìm kiếm và kéo video/ảnh dọc (9:16) miễn phí bản quyền thương mại.
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from typing import Any

from core.schema import VideoItem
from providers.base import register, BaseProvider

logger = logging.getLogger(__name__)


@register("stock")
class StockProvider(BaseProvider):
    name = "stock"

    def search(self, keyword: str, limit: int = 20) -> list[VideoItem]:
        return self.fetch_items(keyword, limit)

    def fetch_items(self, topic: str, limit: int = 20) -> list[VideoItem]:
        items: list[VideoItem] = []
        pexels_key = self.config.get("pexels_api_key", "")
        pixabay_key = self.config.get("pixabay_api_key", "")

        # 1. Quét Pexels Video (Ưu tiên video 9:16)
        if pexels_key:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Authorization": pexels_key
                }
                q = urllib.parse.quote(topic)
                url = f"https://api.pexels.com/videos/search?query={q}&orientation=portrait&per_page={min(limit, 20)}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for v in data.get("videos", []):
                        v_files = v.get("video_files", [])
                        # Chọn file HD / SD tốt nhất
                        best_file = next((f for f in v_files if f.get("quality") == "hd"), None) or (v_files[0] if v_files else None)
                        if not best_file:
                            continue
                        
                        link = best_file.get("link", "")
                        items.append(VideoItem(
                            platform="pexels",
                            native_id=f"pexels_v_{v.get('id')}",
                            url=link,
                            play_url=link,
                            title=f"Pexels Video: {topic} ({v.get('user', {}).get('name', 'Pexels')})",
                            author=v.get("user", {}).get("name", "Pexels"),
                            views=10000,
                            likes=v.get("likes", 500),
                            duration=v.get("duration", 15),
                            cover_url=v.get("image", ""),
                            topic=topic,
                            source="stock",
                            raw={
                                "download_url": link,
                                "license": "Pexels License (Commercial Free)"
                            }
                        ))
            except Exception as exc:
                logger.warning(f"Lỗi fetch Pexels Video cho topic '{topic}': {exc}")

        # 2. Quét Pixabay Photo/Video bổ sung
        if pixabay_key and len(items) < limit:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                q = urllib.parse.quote(topic)
                url = f"https://pixabay.com/api/?key={pixabay_key}&q={q}&image_type=photo&per_page={min(limit, 20)}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for hit in data.get("hits", []):
                        img_url = hit.get("largeImageURL") or hit.get("webformatURL") or ""
                        items.append(VideoItem(
                            platform="pixabay",
                            native_id=f"pixabay_p_{hit.get('id')}",
                            url=img_url,
                            play_url=img_url,
                            title=f"Pixabay Image: {hit.get('tags', topic)}",
                            author=hit.get("user", "Pixabay"),
                            views=hit.get("views", 5000),
                            likes=hit.get("likes", 100),
                            duration=5.0,  # Ảnh tĩnh mặc định 5s
                            cover_url=img_url,
                            topic=topic,
                            source="stock",
                            raw={
                                "download_url": img_url,
                                "license": "Pixabay License (Commercial Free)"
                            }
                        ))
            except Exception as exc:
                logger.warning(f"Lỗi fetch Pixabay cho topic '{topic}': {exc}")

        return items
