"""
Pixabay — ảnh + video, Content License cho phép dùng thương mại.
API key miễn phí: https://pixabay.com/api/docs/

Lưu ý ToS: Pixabay yêu cầu tải file về, không hotlink trực tiếp trong
sản phẩm cuối. Giai đoạn sau nên thêm bước tải media về ./data/media/.
"""

from __future__ import annotations

from models import Doc, License, utcnow
from .base import SourceAdapter

PIXABAY_LICENSE = dict(
    id="pixabay-content-license",
    commercial_use=True,
    modification_allowed=True,
    attribution_required=False,
    license_url="https://pixabay.com/service/license-summary/",
)


class PixabayAdapter(SourceAdapter):
    name = "pixabay"
    source_type = "image"
    capabilities = {"search"}
    requires_key = True
    rate_limit_per_min = 100

    BASE = "https://pixabay.com/api/"

    async def search(self, query: str, limit: int = 20) -> list[Doc]:
        if not self.enabled:
            return []
        async with self.client() as c:
            r = await c.get(self.BASE, params={
                "key": self.api_key,
                "q": query,
                "image_type": "photo",
                "safesearch": "true",
                "per_page": max(3, min(limit, 200)),   # API bắt buộc 3..200
            })
            r.raise_for_status()
            data = r.json()

        docs = []
        for h in data.get("hits", []):
            docs.append(Doc(
                source_type="image",
                source_name=self.name,
                source_url=h.get("pageURL", ""),
                title=h.get("tags") or query,
                content=h.get("tags") or "",
                author=h.get("user"),
                media_url=h.get("largeImageURL"),
                thumbnail_url=h.get("webformatURL"),
                width=h.get("imageWidth"),
                height=h.get("imageHeight"),
                license=License(**PIXABAY_LICENSE, verified_at=utcnow()),
                tags=[t.strip() for t in (h.get("tags") or "").split(",") if t.strip()],
                engagement={
                    "views": h.get("views", 0),
                    "downloads": h.get("downloads", 0),
                    "likes": h.get("likes", 0),
                },
                metadata={"pixabay_id": h.get("id")},
            ))
        return docs
