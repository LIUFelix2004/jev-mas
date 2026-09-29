from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


@dataclass
class Config:
    jev_api_key: str = field(default_factory=lambda: _env("TYPESAFE_API_KEY", os.getenv("JEV_API_KEY", "")))
    jev_base_url: str = field(default_factory=lambda: _env("TYPESAFE_BASE_URL", "https://api.typesafe.ai"))
    target_keywords: list[str] = field(
        default_factory=lambda: [k.strip() for k in _env("TARGET_KEYWORDS", "iPhone 15 Pro Max 256G").split(",") if k.strip()]
    )
    max_results: int = field(default_factory=lambda: int(_env("MAX_RESULTS", "30")))
    min_profit: float = field(default_factory=lambda: float(_env("MIN_PROFIT", "200")))
    min_discount_rate: float = field(default_factory=lambda: float(_env("MIN_DISCOUNT_RATE", "0.08")))
    min_confidence: float = field(default_factory=lambda: float(_env("MIN_CONFIDENCE", "0.5")))
    history_days: int = field(default_factory=lambda: int(_env("HISTORY_DAYS", "3")))
    scan_interval_minutes: int = field(default_factory=lambda: int(_env("SCAN_INTERVAL_MINUTES", "15")))
    webhook_url: str = field(default_factory=lambda: _env("WEBHOOK_URL", ""))
    db_path: str = field(default_factory=lambda: _env("DB_PATH", "jev_mas.db"))
    headless: bool = field(default_factory=lambda: _env("HEADLESS", "false").lower() == "true")
