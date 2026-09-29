"""用 Jev 审核闲鱼挂单、评估捡漏机会

每条挂单一次 multi 请求同时问三件事：是不是目标机型整机、成色、有无硬伤。
"""

from __future__ import annotations

import asyncio

from jev_mas.jev.client import ChoiceAnswer, JevClient, NoulAnswer
from jev_mas.models import Condition, Deal, Defect, ProductListing, Vetting

CONDITION_CRITERIA = {
    "like_new": "Like new: 99新/准新/未拆封/充新/S级, no visible wear",
    "good": "Good: 95新/9成新/A级, very light wear",
    "fair": "Fair: 9新/85新/B级, visible scratches or wear",
    "poor": "Poor: 8新 or worse/C级, obvious dents or heavy wear",
}
DEFECT_CRITERIA = {
    "none": "No defects or repairs mentioned",
    "minor": "Minor issue: battery health low or replaced, small screen scratch, slight back cover damage",
    "major": "Major issue: broken or replaced screen, board/Face ID/camera fault, iCloud or ID lock, water damage, heavy repairs",
}


async def vet_listing(jev: JevClient, target: str, listing: ProductListing) -> Vetting:
    resp = await jev.multi(
        f"Target product: {target}\nListing title: {listing.title}\nAsking price: {listing.price:.0f} CNY",
        {
            "is_target": {
                "type": "noul",
                "instructions": (
                    "This listing sells one complete, working unit of exactly the target product "
                    "(same model and storage). It is NOT an accessory, box, parts, rental, "
                    "wanted-to-buy post, bundle, or a different model or storage size."
                ),
            },
            "condition": {
                "type": "choice",
                "instructions": "What cosmetic condition grade does the listing describe",
                "criteria": CONDITION_CRITERIA,
            },
            "defect": {
                "type": "choice",
                "instructions": "What functional defects or repairs does the listing mention",
                "criteria": DEFECT_CRITERIA,
            },
        },
    )
    is_target = resp.answers.get("is_target")
    cond = resp.answers.get("condition")
    defect = resp.answers.get("defect")
    return Vetting(
        is_target=is_target.noul if isinstance(is_target, NoulAnswer) else 0.0,
        condition=Condition(cond.choice) if isinstance(cond, ChoiceAnswer) and cond.choice in CONDITION_CRITERIA else Condition.GOOD,
        defect=Defect(defect.choice) if isinstance(defect, ChoiceAnswer) and defect.choice in DEFECT_CRITERIA else Defect.MINOR,
    )


async def vet_all(
    jev: JevClient, target: str, listings: list[ProductListing], concurrency: int = 8
) -> list[tuple[ProductListing, Vetting]]:
    sem = asyncio.Semaphore(concurrency)

    async def one(item: ProductListing) -> tuple[ProductListing, Vetting] | None:
        async with sem:
            try:
                v = await vet_listing(jev, target, item)
            except Exception:
                return None
        item.condition = v.condition
        return item, v

    return [r for r in await asyncio.gather(*(one(i) for i in listings)) if r]


async def score_deal(jev: JevClient, deal: Deal) -> None:
    """估计这个低价是真捡漏还是骗局/隐藏问题，写回 deal.confidence 和 deal.risk"""
    resp = await jev.multi(
        (
            f"Second-hand listing on Xianyu: {deal.listing.title}\n"
            f"Asking price: {deal.listing.price:.0f} CNY\n"
            f"Typical market price for same model and condition: {deal.reference_price:.0f} CNY "
            f"(from {deal.sample_size} listings)\n"
            f"Discount: {deal.discount:.0f} CNY ({deal.discount_rate:.0%})"
        ),
        {
            "genuine": {
                "type": "noul",
                "instructions": (
                    "This is a genuine underpriced listing worth buying for resale, not a scam "
                    "(e.g. deposit-first, move to WeChat, fake low price bait) and not hiding a defect"
                ),
            },
            "risk": {
                "type": "choice",
                "instructions": "How risky is buying this listing",
                "criteria": {
                    "low": "Low risk: plausible seller motive, discount within normal range",
                    "medium": "Medium risk: some unclear details, verify before paying",
                    "high": "High risk: likely scam, bait price, or undisclosed problem",
                },
            },
        },
    )
    genuine = resp.answers.get("genuine")
    risk = resp.answers.get("risk")
    score = genuine.noul if isinstance(genuine, NoulAnswer) else 0.5
    deal.risk = risk.choice if isinstance(risk, ChoiceAnswer) else ""
    if deal.risk == "high":
        score *= 0.5
    elif deal.risk == "medium":
        score *= 0.8
    deal.confidence = score
