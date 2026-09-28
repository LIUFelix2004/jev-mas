"""用 Jev 做商品匹配

核心问题：不同平台的商品标题格式不同，需要判断是否是同一型号+同一成色。
例如：
  闲鱼: "iPhone 15 Pro Max 256G 原色钛金属 99新 全原"
  转转: "苹果iPhone15ProMax 256GB 深空钛色 准新机"
  拍机堂: "iPhone 15 Pro Max 256G A级"

用 Jev 的 choice 和 noul 快速判断。
"""

from __future__ import annotations

from jev_mas.jev.client import JevClient
from jev_mas.models import Condition, ProductListing


async def classify_condition(jev: JevClient, description: str) -> Condition:
    answer = await jev.choice(
        state=f"二手数码商品描述: {description}",
        question="这个商品的成色等级是什么？",
        options=["like_new", "good", "fair", "poor"],
    )
    try:
        return Condition(answer.selected) if answer.selected else Condition.GOOD
    except ValueError:
        return Condition.GOOD


async def match_score(jev: JevClient, a: ProductListing, b: ProductListing) -> float:
    if a.model_name and b.model_name and a.model_name == b.model_name:
        if a.storage == b.storage and a.condition == b.condition:
            return 1.0

    answer = await jev.noul(
        state=(
            f"商品A: {a.title} (价格{a.price}元, 平台{a.platform.value})\n"
            f"商品B: {b.title} (价格{b.price}元, 平台{b.platform.value})"
        ),
        question="这两个商品是否是同一型号、同一配置、同一成色的二手数码产品？",
    )
    return answer.yes_probability if answer.yes_probability is not None else 0.0
