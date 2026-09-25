"""
Pexels — ảnh + video, giấy phép cho phép dùng thương mại, không bắt ghi nguồn.
API key miễn phí: https://www.pexels.com/api/
"""

from __future__ import annotations

from models import Doc, License, utcnow
from .base import SourceAdapter

PEXELS_LICENSE = dict(
    id="pexels-license",
    commercial_use=True,
    modification_allowed=True,
    attribution_required=False,
    license_url="https://www.pexels.com/license/",
)


class PexelsAdapter(SourceAdapter):
    name = "pexels"
    source_type = "image"
    capabilities = {"search"}
    requires_key = True
    rate_limit_per_min = 200

    BASE = "https://api.pexels.com/v1/search"

    async def search(self, query: str, limit: int = 20) -> list[Doc]:
        if not self.enabled:
            return []
        async with self.client() as c:
            r = await c.get(
                self.BASE,
                params={"query": query, "per_page": min(limit, 80)},
                headers={"Authorization": self.api_key},
            )
            r.raise_for_status()
            data = r.json()

        docs = []
        for p in data.get("photos", []):
            src = p.get("src", {})
            docs.append(Doc(
                source_type="image",
                source_name=self.name,
                source_url=p.get("url", ""),
                title=p.get("alt") or query,
                content=p.get("alt") or "",
                author=p.get("photographer"),
                media_url=src.get("original"),
                thumbnail_url=src.get("medium"),
                width=p.get("width"),
                height=p.get("height"),
                license=License(**PEXELS_LICENSE, verified_at=utcnow()),
                tags=[query],
                metadata={
                    "pexels_id": p.get("id"),
                    "photographer_url": p.get("photographer_url"),
                    "avg_color": p.get("avg_color"),
                },
            ))
        return docs


class PexelsVideoAdapter(PexelsAdapter):
    """Cùng key, khác endpoint. Dùng cho mode=video."""
    name = "pexels_video"
    source_type = "video"
    BASE = "https://api.pexels.com/videos/search"

    async def search(self, query: str, limit: int = 20) -> list[Doc]:
        if not self.enabled:
            return []
        async with self.client() as c:
            r = await c.get(
                self.BASE,
                params={"query": query, "per_page": min(limit, 80)},
                headers={"Authorization": self.api_key},
            )
            r.raise_for_status()
            data = r.json()

        docs = []
        for v in data.get("videos", []):
            files = sorted(
                v.get("video_files", []),
                key=lambda f: (f.get("width") or 0),
                reverse=True,
            )
            docs.append(Doc(
                source_type="video",
                source_name=self.name,
                source_url=v.get("url", ""),
                title=(v.get("user") or {}).get("name", query),
                content=query,
                author=(v.get("user") or {}).get("name"),
                media_url=files[0].get("link") if files else None,
                thumbnail_url=v.get("image"),
                width=v.get("width"),
                height=v.get("height"),
                license=License(**PEXELS_LICENSE, verified_at=utcnow()),
                tags=[query],
                metadata={"duration_sec": v.get("duration")},
            ))
        return docs
