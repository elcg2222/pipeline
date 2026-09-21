"""SQLite store - trái tim của pipeline.

Khác V1: không còn cờ boolean `downloaded`, thay bằng state machine + retry
counter + error log. Nhờ đó mọi stage đều idempotent: chạy lại lệnh bao nhiêu
lần cũng không tải trùng, không bỏ sót job lỗi dở.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .schema import VideoItem

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    uid           TEXT PRIMARY KEY,
    platform      TEXT NOT NULL,
    url           TEXT NOT NULL,
    native_id     TEXT,
    title         TEXT,
    author        TEXT,
    author_id     TEXT,
    views         INTEGER DEFAULT 0,
    likes         INTEGER DEFAULT 0,
    comments      INTEGER DEFAULT 0,
    shares        INTEGER DEFAULT 0,
    collects      INTEGER DEFAULT 0,
    duration      REAL DEFAULT 0,
    created_at    REAL DEFAULT 0,
    cover_url     TEXT,
    play_url      TEXT,
    topic         TEXT,
    source        TEXT,
    score         REAL DEFAULT 0,
    score_detail  TEXT,
    state         TEXT DEFAULT 'discovered',
    phash         TEXT,
    local_path    TEXT,
    attempts      INTEGER DEFAULT 0,
    last_error    TEXT,
    first_seen    REAL,
    last_seen     REAL,
    updated_at    REAL,
    raw           TEXT
);
CREATE INDEX IF NOT EXISTS idx_state   ON videos(state);
CREATE INDEX IF NOT EXISTS idx_score   ON videos(score DESC);
CREATE INDEX IF NOT EXISTS idx_topic   ON videos(topic);
CREATE INDEX IF NOT EXISTS idx_phash   ON videos(phash);
CREATE INDEX IF NOT EXISTS idx_author  ON videos(author_id);

-- lịch sử chỉ số theo thời gian -> tính velocity (view tăng bao nhiêu/giờ)
CREATE TABLE IF NOT EXISTS metrics_history (
    uid   TEXT, ts REAL, views INTEGER, likes INTEGER,
    PRIMARY KEY (uid, ts)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage TEXT, topic TEXT, started REAL, finished REAL,
    ok INTEGER, failed INTEGER, note TEXT
);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- ghi ----------
    def upsert(self, item: VideoItem) -> bool:
        """Trả về True nếu là bản ghi MỚI (chưa từng thấy)."""
        now = time.time()
        cur = self.conn.execute("SELECT state, views FROM videos WHERE uid=?", (item.uid,))
        row = cur.fetchone()
        is_new = row is None

        if is_new:
            self.conn.execute(
                """INSERT INTO videos
                (uid, platform, url, native_id, title, author, author_id,
                 views, likes, comments, shares, collects, duration, created_at,
                 cover_url, play_url, topic, source, score, score_detail, state,
                 first_seen, last_seen, updated_at, raw)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item.uid, item.platform, item.url, item.native_id, item.title,
                 item.author, item.author_id, item.views, item.likes, item.comments,
                 item.shares, item.collects, item.duration, item.created_at,
                 item.cover_url, item.play_url, item.topic, item.source,
                 item.score, json.dumps(item.score_detail, ensure_ascii=False),
                 item.state, now, now, now,
                 json.dumps(item.raw, ensure_ascii=False)[:20000]),
            )
        else:
            # KHÔNG ghi đè state (tránh kéo video đã downloaded về lại discovered)
            self.conn.execute(
                """UPDATE videos SET
                   views=MAX(views,?), likes=MAX(likes,?), comments=MAX(comments,?),
                   shares=MAX(shares,?), collects=MAX(collects,?),
                   title=COALESCE(NULLIF(?,''), title),
                   play_url=COALESCE(NULLIF(?,''), play_url),
                   score=?, score_detail=?, last_seen=?, updated_at=?
                   WHERE uid=?""",
                (item.views, item.likes, item.comments, item.shares, item.collects,
                 item.title, item.play_url, item.score,
                 json.dumps(item.score_detail, ensure_ascii=False), now, now, item.uid),
            )

        self.conn.execute(
            "INSERT OR REPLACE INTO metrics_history VALUES (?,?,?,?)",
            (item.uid, now, item.views, item.likes),
        )
        self.conn.commit()
        return is_new

    def set_state(self, uid: str, state: str, **fields):
        sets = ["state=?", "updated_at=?"]
        vals: list = [state, time.time()]
        for k, v in fields.items():
            sets.append(f"{k}=?")
            vals.append(v)
        vals.append(uid)
        self.conn.execute(f"UPDATE videos SET {','.join(sets)} WHERE uid=?", vals)
        self.conn.commit()

    def bump_attempt(self, uid: str, error: str = ""):
        self.conn.execute(
            "UPDATE videos SET attempts=attempts+1, last_error=?, updated_at=? WHERE uid=?",
            (error[:500], time.time(), uid),
        )
        self.conn.commit()

    # ---------- đọc ----------
    def velocity(self, uid: str) -> float:
        """View tăng thêm mỗi giờ, đo giữa 2 lần crawl gần nhất. 0 nếu mới thấy 1 lần."""
        rows = self.conn.execute(
            "SELECT ts, views FROM metrics_history WHERE uid=? ORDER BY ts DESC LIMIT 2", (uid,)
        ).fetchall()
        if len(rows) < 2:
            return 0.0
        dt = (rows[0]["ts"] - rows[1]["ts"]) / 3600.0
        if dt < 0.25:
            return 0.0
        return max(0.0, (rows[0]["views"] - rows[1]["views"]) / dt)

    def pick(self, state: str, limit: int = 50, max_attempts: int = 3,
             topic: Optional[str] = None) -> list[sqlite3.Row]:
        q = ("SELECT * FROM videos WHERE state=? AND attempts<? "
             + ("AND topic=? " if topic else "")
             + "ORDER BY score DESC LIMIT ?")
        args = [state, max_attempts] + ([topic] if topic else []) + [limit]
        return self.conn.execute(q, args).fetchall()

    def author_counts(self, state: str = "queued") -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT author_id, COUNT(*) c FROM videos WHERE state=? GROUP BY author_id", (state,)
        ).fetchall()
        return {r["author_id"]: r["c"] for r in rows}

    def find_phash_near(self, phash: str, max_distance: int = 6) -> Optional[str]:
        """So khớp perceptual hash để bắt video bị đăng lại ở nền tảng khác."""
        if not phash:
            return None
        try:
            target = int(phash, 16)
        except ValueError:
            return None
        rows = self.conn.execute(
            "SELECT uid, phash FROM videos WHERE phash IS NOT NULL AND phash!='' "
            "AND state IN ('downloaded','exported','dubbed','published')"
        ).fetchall()
        for r in rows:
            try:
                if bin(target ^ int(r["phash"], 16)).count("1") <= max_distance:
                    return r["uid"]
            except ValueError:
                continue
        return None

    def stats(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT state, COUNT(*) c FROM videos GROUP BY state").fetchall()
        return {r["state"]: r["c"] for r in rows}

    def log_run(self, stage: str, topic: str, started: float, ok: int, failed: int, note: str = ""):
        self.conn.execute(
            "INSERT INTO runs (stage,topic,started,finished,ok,failed,note) VALUES (?,?,?,?,?,?,?)",
            (stage, topic, started, time.time(), ok, failed, note[:1000]),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


@contextmanager
def open_store(path) -> Iterator[Store]:
    s = Store(path)
    try:
        yield s
    finally:
        s.close()
