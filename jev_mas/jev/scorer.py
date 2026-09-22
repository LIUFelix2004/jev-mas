"""用 Jev 对套利机会打分

不只看价差，还要综合判断：
- 商品匹配可信度
- 价格是否异常（太低可能是骗子/翻新）
- 历史价差是否稳定
"""

from __future__ import annotations

from jev_mas.jev.client import JevClient
from jev_mas.models import ArbitrageOpportunity


async def score_opportunity(jev: JevClient, opp: ArbitrageOpportunity) -> float:
    result = await jev.score(
        query="这个套利机会是否可靠？考虑价差合理性、商品真实性和操作可行性。",
        content=(
            f"买入: {opp.buy_listing.title} @ {opp.buy_listing.price}元 ({opp.buy_listing.platform.value})\n"
            f"卖出: {opp.sell_listing.title} @ {opp.sell_listing.price}元 ({opp.sell_listing.platform.value})\n"
            f"差价: {opp.price_diff}元 (利润率 {opp.profit_rate:.1%})\n"
            f"成色: 买{opp.buy_listing.condition.value} 卖{opp.sell_listing.condition.value}"
        ),
    )
    return result.score if result.score is not None else 0.0


async def filter_anomalies(jev: JevClient, title: str, price: float) -> bool:
    result = await jev.score(
        query="这个二手数码商品的价格是否正常？过低可能是诈骗或严重问题机。",
        content=f"商品: {title}\n价格: {price}元",
    )
    return (result.score or 0.0) > 0.3
