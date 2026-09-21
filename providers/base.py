from __future__ import annotations

from typing import Callable, Protocol

from core.schema import VideoItem


class BaseProvider:
    """Base class cho tất cả providers"""
    
    name: str = ""
    description: str = ""
    
    def __init__(self, config: dict):
        self.config = config
    
    def available(self) -> tuple[bool, str]:
        """Kiểm tra provider có sẵn sàng không"""
        return True, ""
    
    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        """Search videos theo keyword"""
        raise NotImplementedError


class Provider(Protocol):
    name: str
    platform: str

    def available(self) -> tuple[bool, str]:
        """(sẵn sàng?, lý do nếu không). Được gọi bởi `run.py doctor`."""
        ...

    def search(self, keyword: str, limit: int) -> list[VideoItem]:
        ...


REGISTRY: dict[str, Callable[..., Provider]] = {}


def register(name: str):
    def deco(cls):
        REGISTRY[name] = cls
        cls.name = name
        return cls
    return deco


def build(name: str, cfg: dict) -> Provider:
    if name not in REGISTRY:
        raise KeyError(f"provider không tồn tại: {name}. Có: {list(REGISTRY)}")
    return REGISTRY[name](cfg)
