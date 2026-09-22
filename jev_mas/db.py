"""SQLite 存储层

存储历史价格数据，用于：
- 追踪价格趋势
- 发现稳定套利区间
- 过滤一次性异常价格
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterator

from jev_mas.models import ArbitrageOpportunity, Condition, Platform, ProductListing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    url TEXT,
    model_name TEXT,
    condition TEXT,
    storage TEXT,
    color TEXT,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buy_platform TEXT NOT NULL,
    buy_title TEXT NOT NULL,
    buy_price REAL NOT NULL,
    sell_platform TEXT NOT NULL,
    sell_title TEXT NOT NULL,
    sell_price REAL NOT NULL,
    price_diff REAL NOT NULL,
    profit_rate REAL NOT NULL,
    confidence REAL,
    found_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_model ON listings(model_name);
CREATE INDEX IF NOT EXISTS idx_listings_platform ON listings(platform);
CREATE INDEX IF NOT EXISTS idx_listings_scraped ON listings(scraped_at);
"""


class Database:
    def __init__(self, path: str = "jev_mas.db"):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def save_listing(self, listing: ProductListing) -> None:
        self._conn.execute(
            "INSERT INTO listings (platform, title, price, url, model_name, condition, storage, color, scraped_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                listing.platform.value,
                listing.title,
                listing.price,
                listing.url,
                listing.model_name,
                listing.condition.value,
                listing.storage,
                listing.color,
                (listing.scraped_at or datetime.now(timezone.utc)).isoformat(),
            ),
        )
        self._conn.commit()

    def save_listings(self, listings: list[ProductListing]) -> None:
        self._conn.executemany(
            "INSERT INTO listings (platform, title, price, url, model_name, condition, storage, color, scraped_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    l.platform.value, l.title, l.price, l.url,
                    l.model_name, l.condition.value, l.storage, l.color,
                    (l.scraped_at or datetime.now(timezone.utc)).isoformat(),
                )
                for l in listings
            ],
        )
        self._conn.commit()

    def save_opportunity(self, opp: ArbitrageOpportunity) -> None:
        self._conn.execute(
            "INSERT INTO opportunities "
            "(buy_platform, buy_title, buy_price, sell_platform, sell_title, sell_price, "
            "price_diff, profit_rate, confidence, found_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                opp.buy_listing.platform.value,
                opp.buy_listing.title,
                opp.buy_listing.price,
                opp.sell_listing.platform.value,
                opp.sell_listing.title,
                opp.sell_listing.price,
                opp.price_diff,
                opp.profit_rate,
                opp.confidence,
                (opp.found_at or datetime.now(timezone.utc)).isoformat(),
            ),
        )
        self._conn.commit()

    def get_price_history(self, model_name: str, platform: str | None = None, limit: int = 50) -> list[dict]:
        query = "SELECT * FROM listings WHERE model_name = ?"
        params: list = [model_name]
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        query += " ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in self._conn.execute(query, params)]

    def get_recent_opportunities(self, limit: int = 20) -> list[dict]:
        return [
            dict(row)
            for row in self._conn.execute(
                "SELECT * FROM opportunities ORDER BY found_at DESC LIMIT ?", (limit,)
            )
        ]

    def close(self) -> None:
        self._conn.close()
