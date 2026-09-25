"""
Lưu trữ v0: SQLite + FTS5.

Cố ý KHÔNG dùng Postgres/Meilisearch/pgvector ở giai đoạn này.
Một file .db, không server, không Docker. Khi nào chật thì nâng —
adapter không phải viết lại vì chỉ nói chuyện qua Doc.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from models import Doc, License

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    id              TEXT PRIMARY KEY,
    source_type     TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    title           TEXT,
    content         TEXT,
    author          TEXT,
    published_at    TEXT,
    collected_at    TEXT NOT NULL,
    media_url       TEXT,
    thumbnail_url   TEXT,
    width           INTEGER,
    height          INTEGER,
    license_json    TEXT,
    commercial_use  INTEGER,          -- 1 / 0 / NULL(chưa xác minh)
    language        TEXT,
    tags_json       TEXT,
    engagement_json TEXT,
    metadata_json   TEXT
);

CREATE INDEX IF NOT EXISTS idx_docs_type      ON docs(source_type);
CREATE INDEX IF NOT EXISTS idx_docs_source    ON docs(source_name);
CREATE INDEX IF NOT EXISTS idx_docs_published ON docs(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_docs_comm      ON docs(commercial_use);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    title, content, tags,
    content='docs', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
    INSERT INTO docs_fts(rowid, title, content, tags)
    VALUES (new.rowid, new.title, new.content, new.tags_json);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, title, content, tags)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags_json);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, title, content, tags)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags_json);
    INSERT INTO docs_fts(rowid, title, content, tags)
    VALUES (new.rowid, new.title, new.content, new.tags_json);
END;
"""


class Store:
    def __init__(self, path: str | Path = "data/crawler.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- ghi ----------

    def upsert(self, doc: Doc) -> bool:
        """Trả về True nếu là bản ghi mới, False nếu đã có (dedupe tầng 1)."""
        cur = self.conn.execute("SELECT 1 FROM docs WHERE id = ?", (doc.id,))
        if cur.fetchone():
            return False

        lic = doc.license
        self.conn.execute(
            """INSERT INTO docs (
                id, source_type, source_name, source_url, title, content,
                author, published_at, collected_at, media_url, thumbnail_url,
                width, height, license_json, commercial_use, language,
                tags_json, engagement_json, metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                doc.id, doc.source_type, doc.source_name, doc.source_url,
                doc.title, doc.content, doc.author, doc.published_at,
                doc.collected_at, doc.media_url, doc.thumbnail_url,
                doc.width, doc.height,
                json.dumps(lic.__dict__, ensure_ascii=False),
                None if lic.commercial_use is None else int(lic.commercial_use),
                doc.language,
                json.dumps(doc.tags, ensure_ascii=False),
                json.dumps(doc.engagement, ensure_ascii=False),
                json.dumps(doc.metadata, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return True

    def upsert_many(self, docs: Iterable[Doc]) -> tuple[int, int]:
        new = dup = 0
        for d in docs:
            if self.upsert(d):
                new += 1
            else:
                dup += 1
        return new, dup

    # ---------- đọc ----------

    def search(
        self,
        query: str,
        source_type: str | None = None,
        commercial_only: bool = False,
        limit: int = 20,
    ) -> list[Doc]:
        sql = """
            SELECT d.* FROM docs_fts f
            JOIN docs d ON d.rowid = f.rowid
            WHERE docs_fts MATCH ?
        """
        params: list = [_fts_query(query)]
        if source_type:
            sql += " AND d.source_type = ?"
            params.append(source_type)
        if commercial_only:
            sql += " AND d.commercial_use = 1"
        sql += " ORDER BY bm25(docs_fts) LIMIT ?"
        params.append(limit)

        try:
            rows = self.conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return []
        return [_row_to_doc(r) for r in rows]

    def latest(self, source_type: str | None = None, limit: int = 20) -> list[Doc]:
        sql = "SELECT * FROM docs"
        params: list = []
        if source_type:
            sql += " WHERE source_type = ?"
            params.append(source_type)
        sql += " ORDER BY COALESCE(published_at, collected_at) DESC LIMIT ?"
        params.append(limit)
        return [_row_to_doc(r) for r in self.conn.execute(sql, params).fetchall()]

    def stats(self) -> dict:
        q = self.conn.execute(
            """SELECT source_name, source_type, COUNT(*) n,
                      SUM(CASE WHEN commercial_use = 1 THEN 1 ELSE 0 END) comm
               FROM docs GROUP BY source_name, source_type ORDER BY n DESC"""
        ).fetchall()
        total = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        return {"total": total, "by_source": [dict(r) for r in q]}

    def close(self) -> None:
        self.conn.close()


def _fts_query(q: str) -> str:
    """Bọc từng token trong nháy kép để tránh lỗi cú pháp FTS5."""
    tokens = [t for t in q.replace('"', " ").split() if t]
    return " ".join(f'"{t}"' for t in tokens) or '""'


def _row_to_doc(r: sqlite3.Row) -> Doc:
    lic = License(**json.loads(r["license_json"] or "{}"))
    return Doc(
        source_type=r["source_type"], source_name=r["source_name"],
        source_url=r["source_url"], title=r["title"] or "",
        content=r["content"] or "", author=r["author"],
        published_at=r["published_at"], collected_at=r["collected_at"],
        media_url=r["media_url"], thumbnail_url=r["thumbnail_url"],
        width=r["width"], height=r["height"], license=lic,
        language=r["language"],
        tags=json.loads(r["tags_json"] or "[]"),
        engagement=json.loads(r["engagement_json"] or "{}"),
        metadata=json.loads(r["metadata_json"] or "{}"),
        content_hash=r["id"],
    )
