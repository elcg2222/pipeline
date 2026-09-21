"""Discovery cho Douyin & TikTok.

Không có backend nào ổn định 100% (Douyin đổi chữ ký a_bogus/X-Bogus liên tục),
nên provider này hỗ trợ NHIỀU backend và tự rơi xuống backend tiếp theo khi lỗi.
Cấu hình trong config.yaml -> providers.douyin.backends: [dtk, f2, opencli]

  dtk     : self-hosted Douyin_TikTok_Download_API (docker compose up). Ổn định
            nhất, có identity pool tự vá cookie. REST nên gọi từ Python rất dễ.
  f2       : thư viện Python (pip install f2). Không cần server, nhưng cần cookie
            thật copy từ trình duyệt và phải update f2 thường xuyên.
  opencli : gọi CLI OpenCLI (browser-backed, cần Chrome đã đăng nhập douyin.com).
  apify   : trả phí, không cần bảo trì. Dùng khi cần chạy ổn định cho production.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from core.schema import VideoItem, coerce_int
from core.util import polite_sleep, retry, run_json, which
from providers.base import register

log = logging.getLogger("provider.dytk")

try:
    import requests
except ImportError:                                     # pragma: no cover
    requests = None  # type: ignore


# --------------------------------------------------------------------------
# mapping helpers
# --------------------------------------------------------------------------
def _from_aweme(d: dict, platform: str, topic: str, source: str) -> VideoItem:
    """Map cấu trúc aweme chuẩn của Douyin/TikTok (dtk & f2 đều trả dạng này)."""
    stats = d.get("statistics") or d.get("stats") or {}
    author = d.get("author") or {}
    video = d.get("video") or {}
    aid = str(d.get("aweme_id") or d.get("id") or "")

    play = ""
    for key in ("play_addr_h264", "play_addr", "download_addr", "bit_rate"):
        node = video.get(key)
        if isinstance(node, dict) and node.get("url_list"):
            play = node["url_list"][0]
            break
        if isinstance(node, list) and node:
            n0 = node[0].get("play_addr", {}) if isinstance(node[0], dict) else {}
            if n0.get("url_list"):
                play = n0["url_list"][0]
                break

    cover = ""
    c = video.get("cover") or video.get("origin_cover") or {}
    if isinstance(c, dict) and c.get("url_list"):
        cover = c["url_list"][0]

    url = (f"https://www.douyin.com/video/{aid}" if platform == "douyin"
           else f"https://www.tiktok.com/@{author.get('unique_id','_')}/video/{aid}")

    return VideoItem(
        platform=platform,
        url=d.get("share_url") or url,
        native_id=aid,
        title=d.get("desc") or "",
        author=author.get("nickname") or author.get("unique_id") or "",
        author_id=str(author.get("sec_uid") or author.get("uid") or ""),
        views=coerce_int(stats.get("play_count") or stats.get("playCount")),
        likes=coerce_int(stats.get("digg_count") or stats.get("diggCount")),
        comments=coerce_int(stats.get("comment_count") or stats.get("commentCount")),
        shares=coerce_int(stats.get("share_count") or stats.get("shareCount")),
        collects=coerce_int(stats.get("collect_count") or stats.get("collectCount")),
        duration=(video.get("duration") or d.get("duration") or 0) / 1000.0,
        created_at=float(d.get("create_time") or 0),
        cover_url=cover,
        play_url=play,
        topic=topic,
        source=source,
        raw={"aweme_id": aid},
    )


# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------
class DtkBackend:
    """Douyin_TikTok_Download_API self-hosted (REST)."""

    def __init__(self, cfg: dict):
        self.base = cfg.get("dtk_base_url", "http://127.0.0.1:8080").rstrip("/")
        self.token = cfg.get("dtk_token") or os.getenv("DTK_TOKEN", "")

    def available(self):
        if requests is None:
            return False, "thiếu `pip install requests`"
        try:
            r = requests.get(f"{self.base}/health", timeout=5)
            return (r.status_code < 500), f"HTTP {r.status_code}"
        except Exception as e:
            return False, f"không kết nối được {self.base}: {e}"

    @retry(times=3)
    def search(self, platform: str, keyword: str, limit: int) -> list[dict]:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        r = requests.get(
            f"{self.base}/api/{platform}/web/fetch_general_search_result",
            params={"keyword": keyword, "count": limit, "sort_type": "0",
                    "publish_time": "0", "offset": 0},
            headers=headers, timeout=60,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        items = data.get("data") or data.get("aweme_list") or []
        out = []
        for it in items:
            out.append(it.get("aweme_info") or it)
        return out


class F2Backend:
    """Thư viện f2 (Johnserf-Seed) dùng trực tiếp trong process, không cần server."""

    def __init__(self, cfg: dict):
        self.cookie_douyin = cfg.get("douyin_cookie") or os.getenv("DOUYIN_COOKIE", "")
        self.cookie_tiktok = cfg.get("tiktok_cookie") or os.getenv("TIKTOK_COOKIE", "")
        self.proxy = cfg.get("proxy")

    def available(self):
        try:
            import f2  # noqa: F401
        except ImportError:
            return False, "chưa cài: pip install f2"
        if not self.cookie_douyin:
            return False, "thiếu DOUYIN_COOKIE (copy từ DevTools > Network > request header)"
        return True, "ok"

    def _kwargs(self, platform: str) -> dict:
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
        ref = "https://www.douyin.com/" if platform == "douyin" else "https://www.tiktok.com/"
        return {
            "headers": {"User-Agent": ua, "Referer": ref},
            "proxies": {"http://": self.proxy, "https://": self.proxy},
            "timeout": 20,
            "cookie": self.cookie_douyin if platform == "douyin" else self.cookie_tiktok,
        }

    def search(self, platform: str, keyword: str, limit: int) -> list[dict]:
        import asyncio

        if platform == "douyin":
            from f2.apps.douyin.handler import DouyinHandler as H
        else:
            from f2.apps.tiktok.handler import TiktokHandler as H

        handler = H(self._kwargs(platform))
        # f2 đổi tên method giữa các bản; dò lần lượt các tên đã từng tồn tại.
        fn = None
        for cand in ("fetch_search_videos", "fetch_search_video",
                     "fetch_general_search", "handle_search_video"):
            if hasattr(handler, cand):
                fn = getattr(handler, cand)
                break
        if fn is None:
            raise RuntimeError(
                "Bản f2 hiện tại không có API search. Chạy `pip install -U f2` "
                "hoặc chuyển backend sang dtk."
            )

        async def _go():
            out = []
            res = fn(keyword=keyword, count=limit) if _wants_kw(fn) else fn(keyword, limit)
            if hasattr(res, "__aiter__"):
                async for page in res:
                    out.extend(_unwrap(page))
                    if len(out) >= limit:
                        break
            else:
                out.extend(_unwrap(await res))
            return out[:limit]

        return asyncio.run(_go())


def _wants_kw(fn) -> bool:
    import inspect
    try:
        return "keyword" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return True


def _unwrap(page: Any) -> list[dict]:
    if page is None:
        return []
    if hasattr(page, "_to_dict"):
        page = page._to_dict()
    if isinstance(page, dict):
        for k in ("aweme_list", "data", "item_list"):
            if isinstance(page.get(k), list):
                return [x.get("aweme_info") or x for x in page[k]]
        return [page]
    if isinstance(page, list):
        return page
    return []


class OpenCliBackend:
    """opencli <site> search -f json. Browser-backed: cần Chrome đã login."""

    def __init__(self, cfg: dict):
        self.timeout = cfg.get("opencli_timeout", 180)

    def available(self):
        if not which("opencli"):
            return False, "chưa cài: npm i -g @jackwener/opencli"
        return True, ("lưu ý: `opencli douyin search` là PR chưa merge ở nhánh chính; "
                      "nếu lỗi 'unknown command' hãy dùng backend dtk/f2")

    def search(self, platform: str, keyword: str, limit: int) -> list[dict]:
        rows = run_json(["opencli", platform, "search", keyword,
                         "--limit", str(limit), "-f", "json"], timeout=self.timeout)
        return rows if isinstance(rows, list) else []


class ApifyBackend:
    """Trả phí, không cần bảo trì. Dùng khi cần uptime cao."""

    def __init__(self, cfg: dict):
        self.token = cfg.get("apify_token") or os.getenv("APIFY_TOKEN", "")
        self.actors = cfg.get("apify_actors", {})

    def available(self):
        if requests is None:
            return False, "thiếu requests"
        return (bool(self.token and self.actors), "thiếu APIFY_TOKEN hoặc apify_actors")

    @retry(times=2)
    def search(self, platform: str, keyword: str, limit: int) -> list[dict]:
        actor = self.actors.get(platform)
        if not actor:
            raise RuntimeError(f"chưa cấu hình apify actor cho {platform}")
        r = requests.post(
            f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",
            params={"token": self.token, "timeout": 300},
            json={"keywords": [keyword], "maxItems": limit, "resultsPerPage": limit},
            timeout=310,
        )
        r.raise_for_status()
        return r.json()


BACKENDS = {"dtk": DtkBackend, "f2": F2Backend, "opencli": OpenCliBackend, "apify": ApifyBackend}


# --------------------------------------------------------------------------
# Provider
# --------------------------------------------------------------------------
class _Base:
    platform = ""

    def __init__(self, cfg: dict):
        self.cfg = cfg.get("providers", {}).get(self.platform, {})
        self.order = self.cfg.get("backends", ["dtk", "f2", "opencli"])
        self._built = {n: BACKENDS[n](self.cfg) for n in self.order if n in BACKENDS}

    def available(self):
        msgs = []
        for n in self.order:
            b = self._built.get(n)
            if not b:
                continue
            ok, why = b.available()
            msgs.append(f"{n}={'OK' if ok else 'X'} ({why})")
            if ok:
                return True, " | ".join(msgs)
        return False, " | ".join(msgs) or "không có backend nào"

    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        errors = []
        for n in self.order:
            b = self._built.get(n)
            if not b:
                continue
            ok, why = b.available()
            if not ok:
                errors.append(f"{n}: {why}")
                continue
            try:
                raw = b.search(self.platform, keyword, limit)
                items = [self._map(d, keyword, n) for d in raw]
                items = [i for i in items if i and i.url]
                if items:
                    log.info("[%s/%s] '%s' -> %d video", self.platform, n, keyword, len(items))
                    polite_sleep(*self.cfg.get("sleep_range", (1.5, 4.0)))
                    return items
                errors.append(f"{n}: rỗng")
            except Exception as e:
                log.warning("[%s/%s] lỗi: %s", self.platform, n, e)
                errors.append(f"{n}: {e}")
        log.error("[%s] tất cả backend fail cho '%s': %s", self.platform, keyword, "; ".join(errors))
        return []

    def _map(self, d: dict, topic: str, backend: str) -> VideoItem | None:
        src = f"{self.platform}:{backend}"
        # OpenCLI trả shape phẳng {rank,desc,author,url,plays,likes,...}
        if "url" in d and "aweme_id" not in d and "statistics" not in d:
            return VideoItem(
                platform=self.platform, url=d.get("url", ""),
                title=d.get("desc") or d.get("title") or "",
                author=d.get("author") or "",
                views=coerce_int(d.get("plays") or d.get("views")),
                likes=coerce_int(d.get("likes")),
                comments=coerce_int(d.get("comments")),
                shares=coerce_int(d.get("shares")),
                collects=coerce_int(d.get("collects") or d.get("saves")),
                topic=topic, source=src,
            )
        return _from_aweme(d, self.platform, topic, src)


@register("douyin")
class DouyinProvider(_Base):
    platform = "douyin"


@register("tiktok")
class TiktokProvider(_Base):
    platform = "tiktok"
