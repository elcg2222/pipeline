"""Chấm điểm & lọc.

Nâng cấp so với V1 (view log + engagement + freshness):
  1. VELOCITY  - view tăng/giờ giữa 2 lần crawl. Đây mới là "đang trend",
                 khác hẳn "đã nổi từ 6 ngày trước".
  2. SAVE RATE - tỷ lệ lượt lưu (collect). Trên Douyin đây là tín hiệu ý định
                 mua mạnh nhất; like chỉ là giải trí.
  3. HARD GATE - loại thẳng video sai định dạng trước khi tốn băng thông:
                 duration ngoài khoảng, view quá thấp, engagement ảo (bot).
  4. DIVERSITY - chặn 1 tác giả chiếm hết Top N.
"""
from __future__ import annotations

import math
from typing import Iterable

from .schema import VideoItem


# ---------------- Hard gate ----------------
def hard_filter(item: VideoItem, cfg: dict) -> str | None:
    """Trả về lý do loại, hoặc None nếu pass."""
    f = cfg.get("filters", {})
    if not item.url:
        return "no_url"
    if item.views and item.views < f.get("min_views", 5000):
        return "low_views"
    if item.likes < f.get("min_likes", 100):
        return "low_likes"

    d = item.duration
    if d:
        lo, hi = f.get("min_duration", 8), f.get("max_duration", 180)
        if d < lo:
            return "too_short"
        if d > hi:
            return "too_long"

    if item.age_hours > f.get("max_age_hours", 24 * 45):
        return "too_old"

    # Engagement ảo: like > view là dữ liệu rác / bot farm
    if item.views and item.likes > item.views:
        return "impossible_engagement"

    kw_block = [k.lower() for k in f.get("blocklist_keywords", [])]
    t = (item.title or "").lower()
    if any(k in t for k in kw_block):
        return "blocked_keyword"

    kw_need = [k.lower() for k in f.get("require_any_keywords", [])]
    if kw_need and not any(k in t for k in kw_need):
        return "missing_required_keyword"
    return None


# ---------------- Score ----------------
def score(item: VideoItem, cfg: dict, velocity: float = 0.0) -> tuple[float, dict]:
    w = cfg.get("weights", {})
    v = max(item.views, 1)

    # 1) Quy mô: log để 10M view không nuốt chửng toàn bộ thang điểm
    s_reach = math.log10(v) / 7.0                       # 10 view=0.14 ... 10M=1.0

    # 2) Tương tác
    eng = (item.likes + 3 * item.comments + 5 * item.shares) / v
    s_eng = min(eng / cfg.get("engagement_ceiling", 0.25), 1.0)

    # 3) Ý định mua: lượt lưu
    save_rate = item.collects / v if item.collects else 0.0
    s_save = min(save_rate / cfg.get("save_rate_ceiling", 0.05), 1.0)

    # 4) Độ mới: half-life thay vì cắt cứng 7 ngày
    hl = cfg.get("freshness_halflife_hours", 72)
    s_fresh = 0.5 ** (item.age_hours / hl)

    # 5) Tốc độ lan: log velocity
    s_vel = min(math.log10(velocity + 1) / 4.0, 1.0)    # 10k view/h -> 1.0

    total = (
        w.get("reach", 0.20) * s_reach
        + w.get("engagement", 0.25) * s_eng
        + w.get("save", 0.20) * s_save
        + w.get("freshness", 0.15) * s_fresh
        + w.get("velocity", 0.20) * s_vel
    )

    # Ưu tiên nền tảng (Douyin thường là nguồn gốc, chất lượng review cao nhất)
    total *= cfg.get("platform_boost", {}).get(item.platform, 1.0)

    detail = {
        "reach": round(s_reach, 3), "engagement": round(s_eng, 3),
        "save": round(s_save, 3), "freshness": round(s_fresh, 3),
        "velocity": round(s_vel, 3), "velocity_raw": round(velocity, 1),
    }
    return round(total, 4), detail


def apply_diversity(items: list[VideoItem], max_per_author: int = 2) -> list[VideoItem]:
    """Giữ thứ tự điểm, nhưng mỗi tác giả tối đa N video."""
    seen: dict[str, int] = {}
    out: list[VideoItem] = []
    for it in sorted(items, key=lambda x: x.score, reverse=True):
        key = it.author_id or it.author or "?"
        if seen.get(key, 0) >= max_per_author:
            continue
        seen[key] = seen.get(key, 0) + 1
        out.append(it)
    return out
