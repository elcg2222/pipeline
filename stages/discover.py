from __future__ import annotations

import logging
import time

from core.schema import VideoItem
from core.scoring import apply_diversity, hard_filter, score
from core.store import Store
from providers.base import build

# Import các provider để đăng ký vào registry
import providers.social_discovery  # noqa: F401
import providers.discord_provider  # noqa: F401
import providers.douyin_tiktok     # noqa: F401
import providers.marketplace       # noqa: F401
import providers.reddit_provider   # noqa: F401
import providers.facebook_provider # noqa: F401

log = logging.getLogger("stage.discover")


def run(store: Store, cfg: dict, topics: list[str] | None = None) -> dict:
    topics = topics or cfg["topics"]
    enabled = [p for p, on in cfg.get("enabled_providers", {}).items() if on]
    per_kw = cfg.get("results_per_keyword", 30)
    started = time.time()

    providers = {}
    for name in enabled:
        try:
            p = build(name, cfg)
            ok, why = p.available()
            if not ok:
                log.warning("bỏ qua provider %s: %s", name, why)
                continue
            providers[name] = p
        except Exception as e:
            log.error("không khởi tạo được provider %s: %s", name, e)

    if not providers:
        log.error("Không có provider nào sẵn sàng. Chạy `python run.py doctor`.")
        return {}

    collected: list[VideoItem] = []
    for kw in topics:
        for name, p in providers.items():
            try:
                collected.extend(p.search(kw, per_kw))
            except Exception as e:
                log.error("[%s] '%s' lỗi: %s", name, kw, e)

    # --- dedupe trong lô (cùng uid từ nhiều nguồn) ---
    best: dict[str, VideoItem] = {}
    for it in collected:
        cur = best.get(it.uid)
        if cur is None or it.views > cur.views:
            best[it.uid] = it

    rejected = 0
    scored: list[VideoItem] = []
    for it in best.values():
        reason = hard_filter(it, cfg)
        if reason:
            it.state = "rejected"
            it.score_detail = {"reject": reason}
            store.upsert(it)
            store.set_state(it.uid, "rejected")
            rejected += 1
            continue
        store.upsert(it)                                  # ghi trước để có lịch sử
        it.score, it.score_detail = score(it, cfg, store.velocity(it.uid))
        store.upsert(it)                                  # ghi lại kèm điểm
        scored.append(it)

    # --- chọn Top N, giới hạn số video / tác giả ---
    top_n = cfg.get("top_n_per_run", 20)
    picked = apply_diversity(scored, cfg.get("max_per_author", 2))[:top_n]

    queued = 0
    for it in picked:
        row = store.conn.execute("SELECT state FROM videos WHERE uid=?", (it.uid,)).fetchone()
        if row and row["state"] in ("discovered",):       # chỉ nâng từ discovered
            store.set_state(it.uid, "queued")
            queued += 1

    store.log_run("discover", ",".join(topics), started, queued, rejected,
                  f"thu {len(collected)}, unique {len(best)}")
    log.info("Discovery xong: thu %d, unique %d, loại %d, vào hàng đợi %d",
             len(collected), len(best), rejected, queued)
    return {"collected": len(collected), "unique": len(best),
            "rejected": rejected, "queued": queued}
