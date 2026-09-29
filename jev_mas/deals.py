"""闲鱼捡漏引擎

1. 搜目标机型 → Jev 审核每条挂单（是否目标整机 / 成色 / 硬伤）
2. 合格挂单 + 近几天历史 → 按成色算行情价（中位数）
3. 低于行情一定比例且差额够大的 → Jev 评估风险 → 捡漏候选
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

from jev_mas.jev.client import JevClient
from jev_mas.jev.judge import score_deal
from jev_mas.models import Condition, Deal, ProductListing, Vetting

MIN_SAMPLES = 5


def reference_prices(
    current: list[tuple[ProductListing, Vetting]], history: dict[str, list[float]]
) -> tuple[dict[str, tuple[float, int]], tuple[float, int] | None]:
    """按成色的行情价，以及不分成色的整体行情价；样本不足的成色不给价"""
    by_cond: dict[str, list[float]] = {c.value: list(history.get(c.value, [])) for c in Condition}
    for item, v in current:
        if v.valid:
            by_cond[v.condition.value].append(item.price)
    refs = {c: (median(p), len(p)) for c, p in by_cond.items() if len(p) >= MIN_SAMPLES}
    everything = [p for ps in by_cond.values() for p in ps]
    overall = (median(everything), len(everything)) if len(everything) >= MIN_SAMPLES else None
    return refs, overall


async def find_deals(
    jev: JevClient,
    keyword: str,
    vetted: list[tuple[ProductListing, Vetting]],
    history: dict[str, list[float]],
    min_profit: float,
    min_discount_rate: float,
) -> list[Deal]:
    refs, overall = reference_prices(vetted, history)
    deals: list[Deal] = []
    for item, v in vetted:
        if not v.valid:
            continue
        ref = refs.get(v.condition.value) or overall
        if not ref:
            continue
        price, n = ref
        if price - item.price < min_profit or item.price > price * (1 - min_discount_rate):
            continue
        deal = Deal(listing=item, vetting=v, keyword=keyword, reference_price=price,
                    sample_size=n, found_at=datetime.now(timezone.utc))
        await score_deal(jev, deal)
        deals.append(deal)
    deals.sort(key=lambda d: d.discount * d.confidence, reverse=True)
    return deals
