"""
Openverse — gộp hàng trăm triệu ảnh Creative Commons từ nhiều nguồn.
Không cần key cho mức dùng cơ bản: https://api.openverse.org/v1/

Đây là adapter duy nhất trong v0 mà LICENSE ENGINE thật sự có việc làm:
Pexels/Pixabay luôn cho phép thương mại, còn Openverse trộn lẫn nhiều
giấy phép — trong đó các giấy phép có "nc" (NonCommercial) KHÔNG được
dùng thương mại. Nếu bỏ qua bước này, bạn sẽ đưa ảnh cấm thương mại
cho khách hàng mà không biết.
"""

from __future__ import annotations

from models import Doc, License, utcnow
from .base import SourceAdapter

# Bản đồ giấy phép -> quyền. Nguồn: creativecommons.org
_NO_ATTRIBUTION = {"cc0", "pdm"}
_NON_COMMERCIAL_MARKER = "nc"
_NO_DERIVATIVES_MARKER = "nd"


def resolve_license(code: str | None, version: str | None, url: str | None) -> License:
    code = (code or "").lower().strip()
    if not code:
        return License(id="unknown", license_url=url)

    return License(
        id=f"{code}-{version}" if version else code,
        commercial_use=_NON_COMMERCIAL_MARKER not in code.split("-"),
        modification_allowed=_NO_DERIVATIVES_MARKER not in code.split("-"),
        attribution_required=code not in _NO_ATTRIBUTION,
        license_url=url,
        verified_at=utcnow(),
    )


class OpenverseAdapter(SourceAdapter):
    name = "openverse"
    source_type = "image"
    capabilities = {"search"}
    requires_key = False
    rate_limit_per_min = 60      # ẩn danh: hạn mức thấp, có key thì cao hơn

    BASE = "https://api.openverse.org/v1/images/"

    async def search(self, query: str, limit: int = 20) -> list[Doc]:
        params = {"q": query, "page_size": min(limit, 20)}
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with self.client() as c:
            r = await c.get(self.BASE, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()

        docs = []
        for it in data.get("results", []):
            lic = resolve_license(
                it.get("license"), it.get("license_version"), it.get("license_url")
            )
            lic.attribution_text = it.get("attribution")
            docs.append(Doc(
                source_type="image",
                source_name=self.name,
                source_url=it.get("foreign_landing_url") or it.get("url", ""),
                title=it.get("title") or query,
                content=it.get("title") or "",
                author=it.get("creator"),
                media_url=it.get("url"),
                thumbnail_url=it.get("thumbnail"),
                width=it.get("width"),
                height=it.get("height"),
                license=lic,
                tags=[t.get("name") for t in (it.get("tags") or []) if t.get("name")],
                metadata={
                    "openverse_id": it.get("id"),
                    "provider": it.get("provider"),
                },
            ))
        return docs
