"""
Hợp đồng chung cho mọi nguồn.

Thêm một trang mới = thêm một file trong thư mục này, không đụng phần còn lại.
Đây là toàn bộ lý do dự án không biến thành 8 script rời rạc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from models import Doc

USER_AGENT = "crawler-tool/0.1 (+contact: your-email@example.com)"


class SourceAdapter(ABC):
    name: str = "unnamed"
    source_type: str = "unknown"        # image | video | news | discussion
    capabilities: set[str] = set()      # {"search", "poll"}
    requires_key: bool = False
    rate_limit_per_min: int = 60

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) if self.requires_key else True

    async def search(self, query: str, limit: int = 20) -> list[Doc]:
        """Tìm theo từ khoá (cho Query Loop). Adapter không hỗ trợ thì trả []."""
        return []

    async def poll(self, cursor: Any = None) -> tuple[list[Doc], Any]:
        """Kéo nội dung mới theo lịch (cho Ingest Loop)."""
        return [], cursor

    async def health(self) -> bool:
        """
        Nguồn còn sống không. v0 chỉ thử một truy vấn nhỏ.
        Giai đoạn sau: chạy hàng ngày, cảnh báo khi adapter chết âm thầm.
        """
        try:
            return len(await self.search("test", limit=1)) >= 0
        except Exception:
            return False

    # tiện ích dùng chung
    @staticmethod
    def client(timeout: float = 15.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
