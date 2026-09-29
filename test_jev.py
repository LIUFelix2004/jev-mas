"""快速测试 Jev API 连通性

对照文档的三种题型: noul / choice / score
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def test():
    from jev_mas.jev.client import JevClient

    api_key = os.getenv("TYPESAFE_API_KEY", "")
    if not api_key:
        print("错误: 请在 .env 中设置 TYPESAFE_API_KEY")
        return

    base_url = os.getenv("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:20]}...{api_key[-8:]}")

    async with JevClient(api_key, base_url) as jev:
        # ---- 测试 1: Noul ----
        print("\n--- 测试 Noul (是/否判断) ---")
        ans = await jev.noul(
            state="Product: iPhone 15 Pro Max 256G 99新\nPrice: 200 CNY",
            instructions="This second-hand phone price is suspiciously low and likely a scam",
        )
        print(f"  noul (是骗局的概率): {ans.noul}")

        # ---- 测试 2: Choice ----
        print("\n--- 测试 Choice (选择) ---")
        ans = await jev.choice(
            state="二手商品描述: iPhone 15 Pro Max 256G 原色钛金属 99新 无拆无修",
            instructions="What condition grade is this product",
            criteria={
                "like_new": "Almost new, 99% condition",
                "good": "Good condition, minor signs of use",
                "fair": "Fair, visible wear",
                "poor": "Poor, significant damage",
            },
        )
        print(f"  选择: {ans.choice}")
        print(f"  置信度: {ans.confidence}")
        print(f"  概率: {ans.probabilities}")

        # ---- 测试 3: Multi (一次请求多个问题) ----
        print("\n--- 测试 Multi (批量判断) ---")
        resp = await jev.multi(
            state=(
                "Product A: iPhone 15 Pro Max 256G 99新 闲鱼 5800元\n"
                "Product B: 苹果iPhone15ProMax 256GB 准新机 转转 6200元"
            ),
            questions={
                "same_product": {
                    "type": "noul",
                    "instructions": "These two listings are the same product model and configuration",
                },
                "risk_level": {
                    "type": "choice",
                    "instructions": "Risk level of buying from listing A and selling at listing B price",
                    "criteria": {
                        "low": "Normal market spread",
                        "medium": "Some uncertainty",
                        "high": "Likely too good to be true",
                    },
                },
                "deal_quality": {
                    "type": "score",
                    "instructions": "How good is this resale deal",
                    "criteria": [
                        "Bad deal, not worth the effort",
                        "Marginal, barely profitable",
                        "Decent spread, worth considering",
                        "Great opportunity, clear profit",
                    ],
                },
            },
        )

        print(f"  模型: {resp.model}")
        print(f"  token用量: 输入{resp.input_tokens} 输出{resp.output_tokens}")
        for qid, ans in resp.answers.items():
            print(f"  [{qid}] {ans}")

    print("\n✓ 所有测试通过!")


if __name__ == "__main__":
    asyncio.run(test())
