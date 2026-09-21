"""Nguồn video từ sàn nguồn hàng (1688/Taobao) và YouTube Shorts.

1688 khác hẳn Douyin: không có "view/like". Video ở đây là video mô tả sản phẩm
trên trang chi tiết. Nên KHÔNG chấm điểm bằng engagement, mà bằng tín hiệu
thương mại: số lượng đã bán, số người mua lặp lại, giá.
=> `views` được gán = số lượng đã bán để tái dùng thang điểm reach.
"""
from __future__ import annotations

import logging
import time

from core.schema import VideoItem, coerce_int
from core.util import run_json, which
from providers.base import register

log = logging.getLogger("provider.market")


@register("1688")
class Market1688Provider:
    platform = "1688"

    def __init__(self, cfg: dict):
        self.cfg = cfg.get("providers", {}).get("1688", {})
        self.timeout = self.cfg.get("timeout", 240)

    def available(self):
        if not which("opencli"):
            return False, "chưa cài: npm i -g @jackwener/opencli"
        if not which("yt-dlp"):
            return False, "opencli cần yt-dlp để tải video 1688: pip install -U yt-dlp"
        return True, "cần Chrome đang mở + đã đăng nhập 1688.com (browser bridge)"

    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        try:
            rows = run_json(["opencli", "1688", "search", keyword,
                             "--limit", str(limit), "-f", "json"], timeout=self.timeout)
        except Exception as e:
            log.error("[1688] search lỗi: %s", e)
            return []

        out: list[VideoItem] = []
        for r in rows if isinstance(rows, list) else []:
            offer_id = str(r.get("offerId") or r.get("id") or "")
            if not offer_id:
                continue
            sold = coerce_int(r.get("sold") or r.get("saleCount") or r.get("tradeCount"))
            if sold < self.cfg.get("min_sold", 300):
                continue
            out.append(VideoItem(
                platform="1688",
                url=f"https://detail.1688.com/offer/{offer_id}.html",
                native_id=offer_id,
                title=r.get("title") or r.get("subject") or "",
                author=r.get("company") or r.get("sellerName") or "",
                author_id=str(r.get("sellerId") or ""),
                views=sold,                       # dùng lượng bán làm reach
                likes=coerce_int(r.get("repeatRate") or 0),
                created_at=time.time(),           # sàn không trả ngày đăng video
                topic=keyword,
                source="1688:opencli",
                raw={"price": r.get("price"), "sold": sold},
            ))
        log.info("[1688] '%s' -> %d offer có tiềm năng", keyword, len(out))
        return out


@register("youtube")
class YoutubeShortsProvider:
    platform = "youtube"

    def __init__(self, cfg: dict):
        self.cfg = cfg.get("providers", {}).get("youtube", {})

    def available(self):
        found = which("yt-dlp")
        return (bool(found), "sẵn sàng" if found else "chưa cài: pip install -U yt-dlp")

    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        """Dùng ytsearch của yt-dlp: không cần API key, không quota."""
        import json as _json
        from core.util import run_cmd

        code, out, err = run_cmd(
            ["yt-dlp", f"ytsearch{limit}:{keyword} #shorts",
             "--flat-playlist", "--dump-json", "--no-warnings",
             "--match-filter", "duration < 181"], timeout=180)
        if code != 0:
            log.error("[youtube] yt-dlp lỗi: %s", err[:300])
            return []

        items = []
        for line in out.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = _json.loads(line)
            except _json.JSONDecodeError:
                continue
            vid = d.get("id", "")
            if not vid:
                continue
            items.append(VideoItem(
                platform="youtube",
                url=f"https://www.youtube.com/watch?v={vid}",
                native_id=vid,
                title=d.get("title") or "",
                author=d.get("uploader") or d.get("channel") or "",
                author_id=d.get("channel_id") or "",
                views=coerce_int(d.get("view_count")),
                likes=coerce_int(d.get("like_count")),
                duration=float(d.get("duration") or 0),
                created_at=float(d.get("timestamp") or 0) or time.time(),
                topic=keyword,
                source="youtube:yt-dlp",
            ))
        log.info("[youtube] '%s' -> %d video", keyword, len(items))
        return items
