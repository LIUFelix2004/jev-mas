from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Platform(Enum):
    XIANYU = "xianyu"
    ZHUANZHUAN = "zhuanzhuan"
    PAIJITANG = "paijitang"


class Condition(Enum):
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class ProductListing:
    platform: Platform
    title: str
    price: float
    url: str
    model_name: str = ""
    condition: Condition = Condition.GOOD
    storage: str = ""
    color: str = ""
    scraped_at: datetime | None = None
    raw_data: dict | None = None

    @property
    def normalized_key(self) -> str:
        return f"{self.model_name}|{self.storage}|{self.condition.value}"


@dataclass
class ArbitrageOpportunity:
    buy_listing: ProductListing
    sell_listing: ProductListing
    price_diff: float
    profit_rate: float
    confidence: float = 0.0
    found_at: datetime | None = None

    @property
    def summary(self) -> str:
        return (
            f"{self.buy_listing.model_name} "
            f"买:{self.buy_listing.platform.value}@{self.buy_listing.price:.0f} "
            f"卖:{self.sell_listing.platform.value}@{self.sell_listing.price:.0f} "
            f"差价:{self.price_diff:.0f} ({self.profit_rate:.1%})"
        )
