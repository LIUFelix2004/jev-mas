"""闲鱼爬虫

闲鱼是纯 C2C 平台，价格完全由卖家决定。
H5 版: m.goofish.com (原 m.idle.fish.com)
需要淘宝/支付宝登录态。

策略：
1. 通过 H5 页面搜索关键词
2. 解析搜索结果列表
3. 提取价格、标题、链接
"""

from __future__ import annotations

from datetime import datetime, timezone

from jev_mas.models import Platform, ProductListing
from jev_mas.scrapers.base import BaseScraper


class XianyuScraper(BaseScraper):
    platform = Platform.XIANYU
    BASE_URL = "https://m.goofish.com"

    async def search(self, keyword: str, max_results: int = 20) -> list[ProductListing]:
        page = await self.new_page()
        try:
            await page.goto(f"{self.BASE_URL}/search?q={keyword}", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            items = await page.query_selector_all('[class*="item"], [class*="card"], [class*="feed"]')
            listings: list[ProductListing] = []

            for item in items[:max_results]:
                try:
                    title_el = await item.query_selector('[class*="title"]')
                    price_el = await item.query_selector('[class*="price"]')
                    if not title_el or not price_el:
                        continue

                    title = (await title_el.inner_text()).strip()
                    price_text = (await price_el.inner_text()).strip()
                    price = float("".join(c for c in price_text if c.isdigit() or c == ".") or "0")
                    if price <= 0:
                        continue

                    link_el = await item.query_selector("a")
                    href = await link_el.get_attribute("href") if link_el else ""
                    url = f"{self.BASE_URL}{href}" if href and not href.startswith("http") else (href or "")

                    listings.append(ProductListing(
                        platform=self.platform,
                        title=title,
                        price=price,
                        url=url,
                        scraped_at=datetime.now(timezone.utc),
                    ))
                except Exception:
                    continue

            return listings
        finally:
            await page.close()

    async def get_recycle_price(self, model_name: str, condition: str) -> float | None:
        return None
