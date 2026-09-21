"""
Providers Registry - Quản lý tất cả video providers
"""

from .base import BaseProvider
from core.schema import VideoItem
from .douyin_tiktok import DouyinProvider, TiktokProvider
from .social_discovery import RedditProvider as SocialRedditProvider, InstagramProvider
from .discord_provider import DiscordProvider
from .marketplace import Market1688Provider, YoutubeShortsProvider
from .reddit_provider import RedditProvider
from .facebook_provider import FacebookProvider

__all__ = [
    'BaseProvider',
    'VideoItem',
    'DouyinProvider',
    'TiktokProvider',
    'InstagramProvider',
    'DiscordProvider',
    'RedditProvider',
    'FacebookProvider',
    'Market1688Provider',
    'YoutubeShortsProvider',
]

# Registry để dynamically load providers
PROVIDERS_REGISTRY = {
    'douyin': DouyinProvider,
    'tiktok': TiktokProvider,
    'youtube': YoutubeShortsProvider,
    'bilibili': YoutubeShortsProvider,  # tạm thời dùng chung với YouTube
    'instagram': InstagramProvider,
    'discord': DiscordProvider,
    'reddit': RedditProvider,
    'facebook': FacebookProvider,
    '1688': Market1688Provider,
}


def get_provider(name: str, config: dict) -> BaseProvider:
    """Lấy provider instance theo tên"""
    provider_class = PROVIDERS_REGISTRY.get(name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}")
    return provider_class(config)


def list_providers() -> list:
    """Liệt kê tất cả providers có sẵn"""
    return list(PROVIDERS_REGISTRY.keys())
