"""快速测试 Jev API 连通性"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def test():
    from jev_mas.jev.client import JevClient

    api_key = os.getenv("TYPESAFE_API_KEY", os.getenv("JEV_API_KEY", ""))
    base_url = os.getenv("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:20]}...{api_key[-8:]}")

    async with JevClient(api_key, base_url) as jev:
        print("\n--- 测试 Noul (是/否判断) ---")
        ans = await jev.noul(
            state="商品: iPhone 15 Pro Max 256G 99新\n价格: 200元",
            question="这个二手手机的价格是否正常？200元买iPhone15ProMax明显过低。",
        )
        print(f"  yes概率: {ans.yes_probability}")
        print(f"  置信度: {ans.confidence}")

        print("\n--- 测试 Choice (选择) ---")
        ans = await jev.choice(
            state="商品描述: iPhone 15 Pro Max 256G 原色钛金属 99新 无拆无修 全原装",
            question="这个商品的成色等级？",
            options=["like_new", "good", "fair", "poor"],
        )
        print(f"  选择: {ans.selected}")
        print(f"  概率: {ans.probabilities}")

        print("\n--- 测试 Multi (批量判断) ---")
        resp = await jev.multi(
            state=(
                "商品A: iPhone 15 Pro Max 256G 99新 闲鱼 价格5800元\n"
                "商品B: 苹果iPhone15ProMax 256GB 准新机 转转 价格6200元"
            ),
            questions={
                "same_product": {
                    "type": "noul",
                    "instructions": "这两个是否是同一型号同一配置的商品？",
                },
                "arbitrage_quality": {
                    "type": "score",
                    "instructions": "从闲鱼5800买入转转6200卖出，这个套利机会质量如何？",
                },
            },
        )
        for qid, ans in resp.answers.items():
            print(f"  {qid}: type={ans.answer_type} conf={ans.confidence}")
            if ans.yes_probability is not None:
                print(f"    yes概率: {ans.yes_probability}")
            if ans.score_value is not None:
                print(f"    分数: {ans.score_value}")

    print("\n✓ 所有测试通过!")


if __name__ == "__main__":
    asyncio.run(test())
