"""用 Jev 做商品匹配

不同平台的商品标题格式不同，需要判断是否是同一型号+同一成色。
例如：
  闲鱼: "iPhone 15 Pro Max 256G 原色钛金属 99新 全原"
  转转: "苹果iPhone15ProMax 256GB 深空钛色 准新机"
  拍机堂: "iPhone 15 Pro Max 256G A级"
"""

from __future__ import annotations

from jev_mas.jev.client import JevClient
from jev_mas.models import Condition, ProductListing


async def classify_condition(jev: JevClient, description: str) -> Condition:
    answer = await jev.choice(
        state=f"二手数码商品描述: {description}",
        instructions="What condition grade is this product",
        criteria={
            "like_new": "几乎全新/99新/未拆封/准新/S级/充新",
            "good": "95新/9成新/A级/良好/无划痕",
            "fair": "9新/85新/B级/有使用痕迹/轻微划痕",
            "poor": "8新以下/C级/明显磨损/有磕碰",
        },
    )
    try:
        return Condition(answer.choice) if answer.choice else Condition.GOOD
    except ValueError:
        return Condition.GOOD


async def match_score(jev: JevClient, a: ProductListing, b: ProductListing) -> float:
    if a.model_name and b.model_name and a.model_name == b.model_name:
        if a.storage == b.storage and a.condition == b.condition:
            return 1.0

    answer = await jev.noul(
        state=(
            f"Product A: {a.title} (price {a.price} CNY, platform {a.platform.value})\n"
            f"Product B: {b.title} (price {b.price} CNY, platform {b.platform.value})"
        ),
        instructions="These two listings are the same product model, same storage, and same condition grade",
    )
    return answer.noul
