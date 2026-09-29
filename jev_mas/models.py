from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Platform(Enum):
    XIANYU = "xianyu"


class Condition(Enum):
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class Defect(Enum):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"


CONDITION_LABELS = {"like_new": "准新", "good": "良好", "fair": "一般", "poor": "较差"}
DEFECT_LABELS = {"none": "无", "minor": "小问题", "major": "大问题"}


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
    def item_id(self) -> str:
        m = re.search(r"(?:[?&]id=|/item/)(\d+)", self.url)
        return m.group(1) if m else self.url


@dataclass
class Vetting:
    """Jev 对一条挂单的审核结果"""

    is_target: float
    condition: Condition
    defect: Defect

    @property
    def valid(self) -> bool:
        return self.is_target >= 0.6 and self.defect != Defect.MAJOR


@dataclass
class Deal:
    listing: ProductListing
    vetting: Vetting
    keyword: str
    reference_price: float
    sample_size: int
    confidence: float = 0.0
    risk: str = ""
    found_at: datetime | None = None

    @property
    def discount(self) -> float:
        return self.reference_price - self.listing.price

    @property
    def discount_rate(self) -> float:
        return self.discount / self.reference_price if self.reference_price else 0.0
