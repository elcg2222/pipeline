#!/usr/bin/env python3
"""
MCP server — cửa cho AI Agent.

Đây là điểm khác biệt lớn nhất so với việc để agent tự search web:
agent gọi search_topic("biển", mode="image", commercial_only=True) và nhận
JSON có cấu trúc kèm trường license đã xác minh — không phải đoạn văn xuôi.

Chạy:   pip install "mcp[cli]"
        python mcp_server.py

Khai báo trong Claude Desktop / Claude Code:
{
  "mcpServers": {
    "crawler-tool": {
      "command": "python",
      "args": ["/duong/dan/den/crawler-tool/mcp_server.py"]
    }
  }
}
"""

from __future__ import annotations

import json

import config
from router import Router
from storage import Store

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise SystemExit('Thiếu thư viện MCP. Chạy: pip install "mcp[cli]"')

mcp = FastMCP("crawler-tool")


@mcp.tool()
async def search_topic(
    query: str,
    mode: str = "all",
    limit: int = 15,
    commercial_only: bool = False,
) -> str:
    """
    Tìm nội dung theo chủ đề trên nhiều nguồn cùng lúc.

    Args:
        query: từ khoá chủ đề.
        mode: all | image | video | news | news_fast (news_fast ưu tiên tin mới nhất).
        limit: số kết quả tối đa.
        commercial_only: chỉ trả nội dung đã xác minh được dùng thương mại.
    """
    adapters = config.build_adapters(
        include_news=mode in ("news", "news_fast", "all")
    )
    router = Router(adapters, deadline_sec=config.DEADLINE_SEC)
    docs = await router.search(query, mode=mode, limit=limit,
                              commercial_only=commercial_only)
    return json.dumps([_slim(d) for d in docs], ensure_ascii=False, indent=2)


@mcp.tool()
async def search_archive(query: str, source_type: str | None = None,
                         limit: int = 15) -> str:
    """Tìm trong kho đã cào sẵn (nhanh, không gọi mạng ra ngoài)."""
    store = Store(config.DB_PATH)
    docs = store.search(query, source_type=source_type, limit=limit)
    store.close()
    return json.dumps([_slim(d) for d in docs], ensure_ascii=False, indent=2)


@mcp.tool()
async def archive_stats() -> str:
    """Thống kê kho: có bao nhiêu bản ghi, từ nguồn nào."""
    store = Store(config.DB_PATH)
    s = store.stats()
    store.close()
    return json.dumps(s, ensure_ascii=False, indent=2)


def _slim(d) -> dict:
    """Bớt trường để không đốt context của agent."""
    return {
        "title": d.title,
        "source": d.source_name,
        "type": d.source_type,
        "url": d.source_url,
        "media_url": d.media_url,
        "published_at": d.published_at,
        "author": d.author,
        "score": round(d.score, 3),
        "license": {
            "id": d.license.id,
            "commercial_use": d.license.commercial_use,
            "attribution_required": d.license.attribution_required,
            "attribution_text": d.license.attribution_text,
        },
        "excerpt": (d.content or "")[:300],
    }


if __name__ == "__main__":
    mcp.run()
