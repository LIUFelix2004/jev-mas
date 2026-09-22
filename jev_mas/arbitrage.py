"""套利计算引擎

核心流程：
1. 从各平台获取同类商品价格
2. 用 Jev 匹配同一型号/成色的商品
3. 计算价差
4. 用 Jev 评估套利机会可信度
5. 过滤掉异常值和低质量机会
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations

from jev_mas.jev.client import JevClient
from jev_mas.jev.matcher import match_score
from jev_mas.jev.scorer import filter_anomalies, score_opportunity
from jev_mas.models import ArbitrageOpportunity, ProductListing


async def find_opportunities(
    listings_by_platform: dict[str, list[ProductListing]],
    jev: JevClient,
    min_profit: float = 50.0,
    match_threshold: float = 0.7,
) -> list[ArbitrageOpportunity]:
    all_platforms = list(listings_by_platform.keys())
    opportunities: list[ArbitrageOpportunity] = []

    for p1, p2 in combinations(all_platforms, 2):
        for buy_item in listings_by_platform[p1]:
            if not await filter_anomalies(jev, buy_item.title, buy_item.price):
                continue

            for sell_item in listings_by_platform[p2]:
                if not await filter_anomalies(jev, sell_item.title, sell_item.price):
                    continue

                score = await match_score(jev, buy_item, sell_item)
                if score < match_threshold:
                    continue

                diff = sell_item.price - buy_item.price
                if diff < min_profit:
                    diff_rev = buy_item.price - sell_item.price
                    if diff_rev >= min_profit:
                        buy_item, sell_item = sell_item, buy_item
                        diff = diff_rev
                    else:
                        continue

                rate = diff / buy_item.price if buy_item.price > 0 else 0
                opp = ArbitrageOpportunity(
                    buy_listing=buy_item,
                    sell_listing=sell_item,
                    price_diff=diff,
                    profit_rate=rate,
                    found_at=datetime.now(timezone.utc),
                )
                opp.confidence = await score_opportunity(jev, opp)
                opportunities.append(opp)

    opportunities.sort(key=lambda o: o.price_diff * o.confidence, reverse=True)
    return opportunities
