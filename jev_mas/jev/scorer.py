"""用 Jev 对套利机会打分

利用 multi() 一次请求并行判断多个问题，减少延迟和 token 消耗。
"""

from __future__ import annotations

from jev_mas.jev.client import JevClient, ChoiceAnswer, NoulAnswer
from jev_mas.models import ArbitrageOpportunity


async def score_opportunity(jev: JevClient, opp: ArbitrageOpportunity) -> float:
    state = (
        f"Buy: {opp.buy_listing.title} @ {opp.buy_listing.price} CNY ({opp.buy_listing.platform.value})\n"
        f"Sell: {opp.sell_listing.title} @ {opp.sell_listing.price} CNY ({opp.sell_listing.platform.value})\n"
        f"Spread: {opp.price_diff} CNY (margin {opp.profit_rate:.1%})\n"
        f"Condition: buy={opp.buy_listing.condition.value} sell={opp.sell_listing.condition.value}"
    )

    resp = await jev.multi(state, {
        "reliable": {
            "type": "noul",
            "instructions": "This arbitrage opportunity is reliable considering price reasonableness, product authenticity, and operational feasibility",
        },
        "risk": {
            "type": "choice",
            "instructions": "What is the risk level of this trade",
            "criteria": {
                "low": "Low risk, normal price spread",
                "medium": "Moderate risk, unusual factors",
                "high": "High risk, possibly fraudulent or impractical",
            },
        },
    })

    reliable = resp.answers.get("reliable")
    risk = resp.answers.get("risk")

    base_score = reliable.noul if isinstance(reliable, NoulAnswer) else 0.5
    if isinstance(risk, ChoiceAnswer):
        if risk.choice == "high":
            base_score *= 0.5
        elif risk.choice == "medium":
            base_score *= 0.8

    return base_score


async def filter_anomalies(jev: JevClient, title: str, price: float) -> bool:
    answer = await jev.noul(
        state=f"Product: {title}\nPrice: {price} CNY",
        instructions="This second-hand electronics price is within normal market range and not suspiciously low",
    )
    return answer.noul > 0.3
