"""
Schema dữ liệu dùng chung cho TẤT CẢ các nguồn.

Nguyên tắc: mọi adapter, dù là API ảnh hay RSS báo, đều phải trả về Doc.
Đây là thứ giữ cho hệ thống không biến thành 8 script rời rạc.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import json


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class License:
    """
    Trường quan trọng nhất của dự án này.

    Quy tắc vàng: không xác minh được thì commercial_use = None (không biết),
    KHÔNG BAO GIỜ mặc định True. Sáu tháng nữa khi cần trả lời
    "ảnh này dùng cho khách hàng được không", đây là thứ cứu bạn.
    """
    id: str = "unknown"                       # "pexels", "cc0", "cc-by-4.0"...
    commercial_use: Optional[bool] = None     # None = chưa xác minh
    modification_allowed: Optional[bool] = None
    attribution_required: Optional[bool] = None
    attribution_text: Optional[str] = None
    license_url: Optional[str] = None
    verified_at: Optional[str] = None

    @property
    def commercial_safe(self) -> bool:
        """Chỉ True khi đã xác minh rõ ràng."""
        return self.commercial_use is True


@dataclass
class Doc:
    source_type: str                 # "image" | "video" | "news" | "discussion"
    source_name: str                 # "pexels", "vnexpress"...
    source_url: str                  # URL trang gốc (để con người mở)
    title: str = ""
    content: str = ""                # text bài báo / mô tả ảnh
    author: Optional[str] = None
    published_at: Optional[str] = None   # ISO8601, None nếu nguồn không cho
    collected_at: str = field(default_factory=utcnow)

    media_url: Optional[str] = None      # link file ảnh/video trực tiếp
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    license: License = field(default_factory=License)
    language: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    engagement: dict[str, Any] = field(default_factory=dict)  # views, likes...
    metadata: dict[str, Any] = field(default_factory=dict)

    content_hash: str = ""
    score: float = 0.0               # điểm xếp hạng, do router gán lúc query

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """
        v0: hash trên URL gốc + tiêu đề -> chỉ bắt được trùng tuyệt đối.
        TODO (giai đoạn sau): thêm SimHash cho bài báo đăng lại,
        pHash cho ảnh cùng nội dung khác kích thước. Xem ROADMAP.md.
        """
        basis = f"{self.source_url}|{self.title}".strip().lower()
        return "sha256:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()

    @property
    def id(self) -> str:
        return self.content_hash

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
