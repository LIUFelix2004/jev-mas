"""SQLite 存储：挂单历史（算行情价用）+ 已推送的捡漏（去重用）"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from jev_mas.models import Deal, ProductListing, Vetting

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    url TEXT,
    condition TEXT,
    defect TEXT,
    is_target REAL,
    valid INTEGER,
    scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_kw ON items(keyword, scraped_at);
CREATE INDEX IF NOT EXISTS idx_items_id ON items(item_id, keyword);

CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    reference_price REAL NOT NULL,
    condition TEXT,
    confidence REAL,
    risk TEXT,
    url TEXT,
    found_at TEXT NOT NULL,
    UNIQUE(item_id, price)
);
"""


class Database:
    def __init__(self, path: str = "jev_mas.db"):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def save_items(self, keyword: str, vetted: list[tuple[ProductListing, Vetting]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.executemany(
            "INSERT INTO items (item_id, keyword, title, price, url, condition, defect, is_target, valid, scraped_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (l.item_id, keyword, l.title, l.price, l.url, v.condition.value, v.defect.value,
                 v.is_target, int(v.valid), now)
                for l, v in vetted
            ],
        )
        self._conn.commit()

    def price_history(self, keyword: str, days: int, exclude_ids: set[str]) -> dict[str, list[float]]:
        """近 N 天合格挂单的价格（每个商品只取最新一次），按成色分组"""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self._conn.execute(
            "SELECT item_id, condition, price FROM items i "
            "WHERE keyword = ? AND valid = 1 AND scraped_at >= ? AND scraped_at = "
            "(SELECT MAX(scraped_at) FROM items WHERE item_id = i.item_id AND keyword = i.keyword)",
            (keyword, since),
        )
        out: dict[str, list[float]] = {}
        for r in rows:
            if r["item_id"] not in exclude_ids:
                out.setdefault(r["condition"], []).append(r["price"])
        return out

    def record_deal(self, deal: Deal) -> bool:
        """记录捡漏；同一商品同一价格已记录过则返回 False（不重复推送）"""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO deals (item_id, keyword, title, price, reference_price, condition, "
            "confidence, risk, url, found_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                deal.listing.item_id, deal.keyword, deal.listing.title, deal.listing.price,
                deal.reference_price, deal.vetting.condition.value, deal.confidence, deal.risk,
                deal.listing.url, (deal.found_at or datetime.now(timezone.utc)).isoformat(),
            ),
        )
        self._conn.commit()
        return cur.rowcount == 1

    def close(self) -> None:
        self._conn.close()
