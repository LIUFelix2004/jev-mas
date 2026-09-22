from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    jev_api_key: str = field(default_factory=lambda: os.getenv("JEV_API_KEY", ""))
    jev_base_url: str = field(default_factory=lambda: os.getenv("JEV_BASE_URL", "https://api.jev.ai"))
    scan_interval_minutes: int = field(default_factory=lambda: int(os.getenv("SCAN_INTERVAL_MINUTES", "15")))
    min_profit_threshold: float = field(default_factory=lambda: float(os.getenv("MIN_PROFIT_THRESHOLD", "50")))
    target_categories: list[str] = field(
        default_factory=lambda: os.getenv("TARGET_CATEGORIES", "手机,平板,笔记本").split(",")
    )
    webhook_url: str = field(default_factory=lambda: os.getenv("WEBHOOK_URL", ""))
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "jev_mas.db"))
    headless: bool = field(default_factory=lambda: os.getenv("HEADLESS", "true").lower() == "true")
