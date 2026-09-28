"""用 Jev 对套利机会打分

利用 Jev 的 multi() 一次性发送多个判断问题，减少延迟：
- 价格异常检测 (noul)
- 套利可信度评估 (score)
"""

from __future__ import annotations

from jev_mas.jev.client import JevClient
from jev_mas.models import ArbitrageOpportunity


async def score_opportunity(jev: JevClient, opp: ArbitrageOpportunity) -> float:
    state = (
        f"买入: {opp.buy_listing.title} @ {opp.buy_listing.price}元 ({opp.buy_listing.platform.value})\n"
        f"卖出: {opp.sell_listing.title} @ {opp.sell_listing.price}元 ({opp.sell_listing.platform.value})\n"
        f"差价: {opp.price_diff}元 (利润率 {opp.profit_rate:.1%})\n"
        f"成色: 买{opp.buy_listing.condition.value} 卖{opp.sell_listing.condition.value}"
    )

    resp = await jev.multi(state, {
        "reliable": {
            "type": "noul",
            "instructions": "这个套利机会是否可靠？考虑价差合理性、商品真实性和操作可行性。",
        },
        "risk": {
            "type": "choice",
            "instructions": "这个交易的风险等级？",
            "criteria": {"low": "低风险", "medium": "中等风险", "high": "高风险"},
        },
    })

    reliable = resp.answers.get("reliable")
    risk = resp.answers.get("risk")

    base_score = reliable.yes_probability if reliable and reliable.yes_probability is not None else 0.5
    if risk and risk.selected == "high":
        base_score *= 0.5
    elif risk and risk.selected == "medium":
        base_score *= 0.8

    return base_score


async def filter_anomalies(jev: JevClient, title: str, price: float) -> bool:
    answer = await jev.noul(
        state=f"商品: {title}\n价格: {price}元",
        question="这个二手数码商品的价格是否正常？过低可能是诈骗或严重问题机。",
    )
    return (answer.yes_probability or 0.0) > 0.3
