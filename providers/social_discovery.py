"""Nguồn discovery cục bộ cho Reddit và Instagram.

Reddit dùng OpenCLI để tái sử dụng phiên Chrome; Instagram dùng Instaloader
với session đã tạo trên máy. Hai nguồn đều chỉ đưa metadata vào hàng đợi, việc
tải file vẫn thống nhất qua stage download (yt-dlp).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.schema import VideoItem, coerce_int
from core.util import run_json, which
from providers.base import register

log = logging.getLogger("provider.social")


def _rows(value: Any) -> list[dict]:
    """Chuẩn hoá các dạng JSON khác nhau giữa phiên bản OpenCLI."""
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        for key in ("items", "posts", "results", "data", "children"):
            data = value.get(key)
            if isinstance(data, list):
                return [x.get("data", x) for x in data if isinstance(x, dict)]
    return []


@register("reddit")
class RedditProvider:
    platform = "reddit"

    def __init__(self, cfg: dict):
        self.cfg = cfg.get("providers", {}).get("reddit", {})

    def available(self):
        if not which("opencli"):
            return False, "chưa cài OpenCLI"
        return True, "cần Chrome đã đăng nhập Reddit + Browser Bridge"

    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        rows = _rows(run_json([
            "opencli", "reddit", "search", keyword,
            "--limit", str(min(limit, self.cfg.get("max_results", limit))), "-f", "json",
        ], timeout=self.cfg.get("timeout", 120)))
        out: list[VideoItem] = []
        for r in rows:
            media = r.get("media") or {}
            media_url = (r.get("url_overridden_by_dest") or r.get("url") or
                         (media.get("reddit_video") or {}).get("fallback_url") or "")
            is_video = bool(r.get("is_video") or (media.get("reddit_video") if isinstance(media, dict) else False)
                            or "v.redd.it" in media_url or "reddit.com/media" in media_url)
            if not is_video or not media_url:
                continue
            permalink = r.get("permalink") or ""
            if permalink.startswith("/"):
                permalink = "https://www.reddit.com" + permalink
            created = r.get("created_utc") or r.get("created") or 0
            try: created = float(created)
            except (TypeError, ValueError): created = 0
            out.append(VideoItem(
                platform="reddit", url=permalink or media_url, native_id=str(r.get("id") or r.get("name") or ""),
                title=r.get("title") or "", author=r.get("author") or "",
                author_id=str(r.get("author_fullname") or r.get("author") or ""),
                views=coerce_int(r.get("view_count")), likes=coerce_int(r.get("score") or r.get("ups")),
                comments=coerce_int(r.get("num_comments")), duration=float(r.get("duration") or 0),
                created_at=created, cover_url=r.get("thumbnail") or r.get("preview", {}).get("images", [{}])[0].get("source", {}).get("url", "") if isinstance(r.get("preview"), dict) else "",
                topic=keyword, source="reddit:opencli", raw={"subreddit": r.get("subreddit")},
            ))
        log.info("[reddit] '%s' -> %d video", keyword, len(out))
        return out


@register("instagram")
class InstagramProvider:
    platform = "instagram"

    def __init__(self, cfg: dict):
        self.cfg = cfg.get("providers", {}).get("instagram", {})

    def available(self):
        try:
            import instaloader  # noqa: F401
        except ImportError:
            return False, "chưa cài: pip install -U instaloader"
        if not self.cfg.get("session_user"):
            return False, "thiếu providers.instagram.session_user (không lưu mật khẩu)"
        return True, "session Instagram cục bộ"

    def _tags(self, topic: str) -> list[str]:
        mapping = self.cfg.get("topic_hashtags", {}) or {}
        tags = mapping.get(topic, [])
        if isinstance(tags, str):
            tags = [tags]
        if tags:
            return [str(tag).lstrip("#") for tag in tags]
        if not self.cfg.get("use_topic_as_hashtag", False):
            return []
        # Chỉ tự suy ra hashtag Latin; tiếng Việt/Trung nên khai báo rõ trong config.
        tag = re.sub(r"[^a-zA-Z0-9_]", "", topic)
        return [tag] if tag else []

    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        import instaloader

        tags = self._tags(keyword)
        if not tags:
            return []
        loader = instaloader.Instaloader(download_pictures=False, download_videos=False,
                                         save_metadata=False, compress_json=False, quiet=True)
        username = self.cfg["session_user"]
        session_file = self.cfg.get("session_file") or None
        loader.load_session_from_file(username, session_file)
        per_tag = min(limit, self.cfg.get("max_per_hashtag", limit))
        out: list[VideoItem] = []
        for tag in tags:
            try:
                hashtag = instaloader.Hashtag.from_name(loader.context, tag)
                count = 0
                for post in hashtag.get_posts():
                    if not post.is_video:
                        continue
                    shortcode = post.shortcode
                    owner = post.owner_profile
                    out.append(VideoItem(
                        platform="instagram", url=f"https://www.instagram.com/p/{shortcode}/", native_id=shortcode,
                        title=(post.caption or "")[:1000], author=owner.username if owner else "",
                        author_id=str(owner.userid) if owner else "", views=coerce_int(getattr(post, "video_view_count", 0)),
                        likes=coerce_int(post.likes), comments=coerce_int(post.comments),
                        duration=float(getattr(post, "video_duration", 0) or 0),
                        created_at=post.date_utc.replace(tzinfo=timezone.utc).timestamp(),
                        cover_url=str(post.url), topic=keyword, source="instagram:instaloader",
                        raw={"hashtag": tag, "typename": getattr(post, "typename", "")},
                    ))
                    count += 1
                    if count >= per_tag:
                        break
            except Exception as exc:
                log.warning("[instagram] hashtag #%s lỗi: %s", tag, exc)
        log.info("[instagram] '%s' -> %d video", keyword, len(out))
        return out
