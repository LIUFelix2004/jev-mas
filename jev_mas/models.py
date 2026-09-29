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


GRADE_TO_CONDITION = {
    "99新": Condition.LIKE_NEW,
    "95新": Condition.LIKE_NEW,
    "9新": Condition.GOOD,
    "85新": Condition.FAIR,
    "8新": Condition.POOR,
}


@dataclass
class RecyclePrice:
    """拍机堂估价页的一个规格：固定型号/容量/渠道/颜色/保修，按成色分档报价"""

    model_name: str
    spec: str
    reference_price: float
    grade_prices: dict[str, float]
    storage: str = ""
    channel: str = ""
    color: str = ""
    warranty: str = ""
    repair_deductions: dict[str, float] | None = None
    scraped_at: datetime | None = None

    def price_for(self, condition: Condition) -> float | None:
        """该成色能拿到的最低档回收价（保守估计）"""
        prices = [p for g, p in self.grade_prices.items() if GRADE_TO_CONDITION.get(g) == condition]
        return min(prices) if prices else None


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
