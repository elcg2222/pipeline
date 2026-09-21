"""Provider discovery cho Discord - lấy video từ attachments trong channels.

Discord cần bot token hoặc user token để access messages có attachments.
Sử dụng discord.py để fetch messages và extract video URLs.
"""
from __future__ import annotations

import logging
from typing import Any

from core.schema import VideoItem, coerce_int
from providers.base import register

log = logging.getLogger("provider.discord")


@register("discord")
class DiscordProvider:
    platform = "discord"

    def __init__(self, cfg: dict):
        self.cfg = cfg.get("providers", {}).get("discord", {})
        self.token = self.cfg.get("bot_token") or self.cfg.get("user_token")
        self.channel_ids = self.cfg.get("channel_ids", [])
        self.max_messages = self.cfg.get("max_messages", 100)

    def available(self) -> tuple[bool, str]:
        if not self.token:
            return False, "thiếu discord.bot_token hoặc discord.user_token trong config"
        try:
            import discord  # noqa: F401
            return True, "discord.py đã cài + có token"
        except ImportError:
            return False, "chưa cài: pip install -U discord.py"

    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        """Tìm video trong Discord channels dựa trên keyword (có thể là topic/hashtag)."""
        try:
            import discord
            from discord.ext import commands
        except ImportError:
            log.error("discord.py chưa được cài đặt")
            return []

        if not self.token:
            log.error("Không có Discord token trong config")
            return []

        out: list[VideoItem] = []
        
        # Tạo intents để đọc messages
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        
        client = discord.Client(intents=intents)

        async def fetch_videos():
            nonlocal out
            await client.wait_until_ready()
            
            for channel_id in self.channel_ids:
                try:
                    channel = await client.fetch_channel(int(channel_id))
                    if not isinstance(channel, discord.TextChannel):
                        continue
                    
                    count = 0
                    async for message in channel.history(limit=self.max_messages):
                        if count >= limit:
                            break
                        
                        # Filter by keyword nếu có
                        if keyword and keyword.lower() not in message.content.lower():
                            continue
                        
                        for attachment in message.attachments:
                            if attachment.filename.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                                count += 1
                                out.append(VideoItem(
                                    platform="discord",
                                    url=attachment.url,
                                    native_id=f"{channel_id}_{message.id}_{attachment.id}",
                                    title=message.content[:200] if message.content else f"Attachment từ {message.author}",
                                    author=str(message.author) if message.author else "unknown",
                                    author_id=str(message.author.id) if message.author else "",
                                    views=0,
                                    likes=0,
                                    comments=0,
                                    duration=0.0,
                                    created_at=message.created_at.timestamp(),
                                    cover_url="",
                                    topic=keyword,
                                    source="discord:attachments",
                                    raw={
                                        "channel_id": str(channel_id),
                                        "message_id": str(message.id),
                                        "filename": attachment.filename,
                                        "size": attachment.size,
                                    },
                                ))
                                
                                if count >= limit:
                                    break
                except Exception as exc:
                    log.warning("[discord] channel %s lỗi: %s", channel_id, exc)
            
            await client.close()

        # Chạy async event loop
        import asyncio
        try:
            asyncio.run(client.start(self.token))
        except Exception as exc:
            log.error("[discord] lỗi khi fetch: %s", exc)

        log.info("[discord] '%s' -> %d videos", keyword, len(out))
        return out

    def search_by_hashtag(self, hashtag: str, limit: int) -> list[VideoItem]:
        """Tìm video theo hashtag trong Discord messages."""
        # Hashtag search tương tự như keyword search
        return self.search(hashtag, limit)
