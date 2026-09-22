"""用 Jev 做商品匹配

核心问题：不同平台的商品标题格式不同，需要判断是否是同一型号+同一成色。
例如：
  闲鱼: "iPhone 15 Pro Max 256G 原色钛金属 99新 全原"
  转转: "苹果iPhone15ProMax 256GB 深空钛色 准新机"
  拍机堂: "iPhone 15 Pro Max 256G A级"

Jev 的 classify 和 score 可以快速做这个判断。
"""

from __future__ import annotations

from jev_mas.jev.client import JevClient
from jev_mas.models import Condition, ProductListing

CONDITION_MAP = {
    "like_new": ["全新", "未拆封", "99新", "准新", "S级", "充新"],
    "good": ["95新", "9成新", "A级", "良好", "无划痕"],
    "fair": ["9新", "85新", "B级", "轻微", "小花"],
    "poor": ["8新以下", "C级", "明显", "有磕碰", "屏幕裂"],
}


async def classify_condition(jev: JevClient, description: str) -> Condition:
    result = await jev.classify(
        content=description,
        categories=["like_new:几乎全新", "good:成色良好", "fair:有使用痕迹", "poor:明显磨损"],
    )
    try:
        return Condition(result.category.split(":")[0]) if result.category else Condition.GOOD
    except (ValueError, AttributeError):
        return Condition.GOOD


async def match_score(jev: JevClient, a: ProductListing, b: ProductListing) -> float:
    if a.model_name and b.model_name and a.model_name == b.model_name:
        if a.storage == b.storage and a.condition == b.condition:
            return 1.0

    result = await jev.score(
        query="这两个商品是否是同一型号、同一配置、同一成色的二手数码产品？",
        content=f"商品A: {a.title} (价格{a.price})\n商品B: {b.title} (价格{b.price})",
    )
    return result.score if result.score is not None else 0.0
