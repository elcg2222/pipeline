"""Đưa URL công khai vào hàng đợi qua metadata của yt-dlp."""
from __future__ import annotations

import json, logging, time
from urllib.parse import urlparse
from core.schema import VideoItem, coerce_int
from core.store import Store
from core.util import run_cmd, which

log = logging.getLogger("stage.import_urls")

def _platform(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if "facebook.com" in host or "fb.watch" in host: return "facebook"
    if "instagram.com" in host or host == "instagr.am": return "instagram"
    if "reddit.com" in host or "redd.it" in host: return "reddit"
    # Discord attachment/CDN URL thường không nằm ở domain discord.com.
    if "discord.com" in host or "discordapp.com" in host or "discordapp.net" in host: return "discord"
    if host in {"x.com", "twitter.com"} or host.endswith(".twitter.com"): return "twitter"
    if "tiktok.com" in host: return "tiktok"
    if "douyin.com" in host: return "douyin"
    return host.split(".")[0] or "web"

def run(store: Store, cfg: dict, urls: list[str]) -> dict:
    if not which("yt-dlp"): raise RuntimeError("Chưa cài yt-dlp. Chạy: pip install -U yt-dlp")
    started, ok, failed = time.time(), 0, 0
    for url in urls:
        code, out, err = run_cmd(["yt-dlp", "--dump-single-json", "--skip-download", "--no-warnings", url], timeout=cfg.get("download", {}).get("timeout", 300))
        if code:
            failed += 1; log.warning("Không đọc được %s: %s", url, (err or out)[:500]); continue
        try: data = json.loads(out)
        except json.JSONDecodeError:
            failed += 1; log.warning("yt-dlp trả metadata không hợp lệ cho %s", url); continue
        item = VideoItem(platform=_platform(data.get("webpage_url") or url), url=data.get("webpage_url") or url,
            native_id=str(data.get("id") or ""), title=data.get("title") or "",
            author=data.get("uploader") or data.get("channel") or "", author_id=str(data.get("uploader_id") or data.get("channel_id") or ""),
            views=coerce_int(data.get("view_count")), likes=coerce_int(data.get("like_count")), comments=coerce_int(data.get("comment_count")),
            duration=float(data.get("duration") or 0), created_at=float(data.get("timestamp") or time.time()),
            cover_url=data.get("thumbnail") or "", topic="manual", source="manual:yt-dlp", raw={"extractor":data.get("extractor_key")})
        store.upsert(item); store.set_state(item.uid, "queued", last_error=""); ok += 1
        log.info("Đã thêm [%s] %s", item.platform, item.title[:80])
    store.log_run("add_url", "manual", started, ok, failed, f"{len(urls)} URL")
    return {"ok": ok, "failed": failed}
