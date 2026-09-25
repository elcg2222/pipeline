"""
Query Loop — thứ biến 8 adapter rời rạc thành MỘT công cụ.

Fan-out song song tới mọi adapter phù hợp, deadline cứng, gộp, dedupe,
xếp hạng. Một nguồn chậm KHÔNG được làm chết cả truy vấn.
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone

from models import Doc
from adapters.base import SourceAdapter

# Trọng số theo chế độ. Đây là PHỎNG ĐOÁN ban đầu — chỉnh sau khi
# nhìn kết quả thật. Đừng coi những con số này là chân lý.
MODE_WEIGHTS = {
    "image":     {"relevance": 0.6, "freshness": 0.0, "engagement": 0.2, "license": 0.2},
    "video":     {"relevance": 0.6, "freshness": 0.0, "engagement": 0.2, "license": 0.2},
    "news":      {"relevance": 0.4, "freshness": 0.5, "engagement": 0.1, "license": 0.0},
    "news_fast": {"relevance": 0.3, "freshness": 0.7, "engagement": 0.0, "license": 0.0},
    "all":       {"relevance": 0.5, "freshness": 0.3, "engagement": 0.1, "license": 0.1},
}

# Hằng số suy giảm độ tươi (giờ): tin nóng quên nhanh, ảnh không quan tâm
FRESHNESS_TAU_HOURS = {"news_fast": 6, "news": 48, "all": 72}


class Router:
    def __init__(self, adapters: list[SourceAdapter], deadline_sec: float = 8.0) -> None:
        self.adapters = [a for a in adapters if a.enabled]
        self.deadline = deadline_sec

    def _pick(self, mode: str) -> list[SourceAdapter]:
        if mode == "all":
            return [a for a in self.adapters if "search" in a.capabilities]
        target = "news" if mode == "news_fast" else mode
        return [a for a in self.adapters
                if a.source_type == target and "search" in a.capabilities]

    async def search(self, query: str, mode: str = "all", limit: int = 20,
                     commercial_only: bool = False) -> list[Doc]:
        chosen = self._pick(mode)
        if not chosen:
            return []

        async def guarded(a: SourceAdapter) -> list[Doc]:
            try:
                return await asyncio.wait_for(
                    a.search(query, limit=limit), timeout=self.deadline
                )
            except asyncio.TimeoutError:
                print(f"  [timeout] {a.name}")
                return []
            except Exception as e:
                print(f"  [lỗi] {a.name}: {type(e).__name__}: {e}")
                return []

        batches = await asyncio.gather(*(guarded(a) for a in chosen))
        docs = [d for b in batches for d in b]

        if commercial_only:
            docs = [d for d in docs if d.license.commercial_safe]

        docs = dedupe(docs)
        rank(docs, query, mode)
        docs.sort(key=lambda d: d.score, reverse=True)
        return docs[:limit]


def dedupe(docs: list[Doc]) -> list[Doc]:
    """
    Dedupe tầng 1: hash tuyệt đối.
    HẠN CHẾ ĐÃ BIẾT: không bắt được bài báo đăng lại với tiêu đề đổi vài chữ.
    Cần SimHash (tin) và pHash (ảnh) — xem ROADMAP.md giai đoạn 2.
    """
    seen: set[str] = set()
    out = []
    for d in docs:
        if d.id in seen:
            continue
        seen.add(d.id)
        out.append(d)
    return out


def rank(docs: list[Doc], query: str, mode: str) -> None:
    w = MODE_WEIGHTS.get(mode, MODE_WEIGHTS["all"])
    tau = FRESHNESS_TAU_HOURS.get(mode, 72)
    max_eng = max((_engagement_value(d) for d in docs), default=0) or 1

    for d in docs:
        d.score = (
            w["relevance"] * _relevance(d, query)
            + w["freshness"] * _freshness(d, tau)
            + w["engagement"] * (_engagement_value(d) / max_eng)
            + w["license"] * (1.0 if d.license.commercial_safe else 0.0)
        )


def _relevance(d: Doc, query: str) -> float:
    """Chấm điểm thô theo tỉ lệ từ khoá khớp. Nâng cấp: BM25 + embedding."""
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return 0.5
    hay = f"{d.title} {d.content} {' '.join(d.tags)}".lower()
    hits = sum(1 for t in terms if t in hay)
    base = hits / len(terms)
    if query.lower() in d.title.lower():
        base = min(1.0, base + 0.3)
    return base


def _freshness(d: Doc, tau_hours: float) -> float:
    """
    BẪY đã gặp khi test: nếu fallback sang collected_at, mọi doc không có
    ngày đăng (ảnh Pexels chẳng hạn) đều được chấm "vừa mới ra lò" = 1.0,
    và ở mode=news_fast chúng đè lên cả bài báo thật đăng sáng nay.
    Không có ngày đăng = KHÔNG BIẾT, không phải MỚI.
    """
    if not d.published_at:
        return 0.15          # điểm trung tính thấp, không phải 0 cũng không phải 1
    try:
        dt = datetime.fromisoformat(d.published_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.15
    age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    return math.exp(-max(age_h, 0) / tau_hours)


def _engagement_value(d: Doc) -> float:
    e = d.engagement or {}
    return float(e.get("downloads", 0) or e.get("views", 0) or e.get("likes", 0) or 0)
