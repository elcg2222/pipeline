"""Schema chuẩn hoá: mọi provider PHẢI trả về VideoItem.

Nguyên tắc: provider chỉ làm 1 việc = lấy dữ liệu thô rồi map sang VideoItem.
Mọi logic lọc/chấm điểm nằm ở core/scoring.py để test được độc lập.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

# Các trạng thái vòng đời. Lưu trong SQLite cột `state`.
STATES = (
    "discovered",    # vừa crawl được
    "queued",        # đã qua scoring + lọc, chờ tải
    "downloading",
    "downloaded",
    "qc_failed",     # tải xong nhưng không đạt chất lượng -> bỏ
    "duplicate",     # trùng nội dung (phash) với video đã có
    "exported",      # đã đẩy sang AutoDub
    "dubbed",        # AutoDub trả về video hoàn thiện
    "published",
    "rejected",      # bị lọc ở khâu scoring
    "error",
)

_ID_PATTERNS = [
    re.compile(r"douyin\.com/video/(\d+)"),
    re.compile(r"douyin\.com/(?:share/video/)?(\d{15,})"),
    re.compile(r"tiktok\.com/@[^/]+/video/(\d+)"),
    re.compile(r"youtube\.com/shorts/([\w-]{6,})"),
    re.compile(r"youtu\.be/([\w-]{6,})"),
    re.compile(r"detail\.1688\.com/offer/(\d+)"),
]


def canonical_url(url: str) -> str:
    """Bỏ query param tracking để 2 link cùng video không bị coi là khác nhau."""
    if not url:
        return ""
    url = url.split("?")[0].split("#")[0].rstrip("/")
    return url.replace("http://", "https://").replace("//m.", "//www.")


def extract_native_id(url: str) -> str:
    for p in _ID_PATTERNS:
        m = p.search(url or "")
        if m:
            return m.group(1)
    return ""


@dataclass
class VideoItem:
    platform: str                 # douyin | tiktok | youtube | 1688 | taobao
    url: str
    title: str = ""
    author: str = ""
    author_id: str = ""
    native_id: str = ""           # aweme_id / video id gốc
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    collects: int = 0             # lượt lưu - tín hiệu mua hàng mạnh nhất trên Douyin
    duration: float = 0.0         # giây
    created_at: float = 0.0       # epoch seconds
    cover_url: str = ""
    play_url: str = ""            # link mp4 không watermark nếu provider trả sẵn
    topic: str = ""               # từ khoá đã sinh ra item này
    source: str = ""              # tên provider
    raw: dict = field(default_factory=dict)

    # Các field pipeline tự điền
    score: float = 0.0
    score_detail: dict = field(default_factory=dict)
    state: str = "discovered"
    phash: str = ""
    local_path: str = ""

    def __post_init__(self):
        self.url = canonical_url(self.url)
        if not self.native_id:
            self.native_id = extract_native_id(self.url)
        if not self.created_at:
            self.created_at = time.time()

    @property
    def uid(self) -> str:
        """Khoá chính. Ưu tiên platform+native_id, fallback hash url."""
        if self.native_id:
            return f"{self.platform}:{self.native_id}"
        return f"{self.platform}:h{hashlib.sha1(self.url.encode()).hexdigest()[:16]}"

    @property
    def age_hours(self) -> float:
        return max(0.0, (time.time() - self.created_at) / 3600.0)

    def to_dict(self) -> dict:
        return asdict(self)


def coerce_int(v, default: int = 0) -> int:
    """Douyin/TikTok hay trả '1.2万', '12.3k', '1,234'."""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().replace(",", "").replace(" ", "")
    if not s:
        return default
    mult = 1.0
    for suf, m in (("万", 1e4), ("亿", 1e8), ("k", 1e3), ("K", 1e3),
                   ("m", 1e6), ("M", 1e6), ("w", 1e4), ("W", 1e4)):
        if s.endswith(suf):
            s, mult = s[: -len(suf)], m
            break
    try:
        return int(float(s) * mult)
    except ValueError:
        return default
