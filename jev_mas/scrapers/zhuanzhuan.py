"""转转爬虫

转转有两个价格体系：
1. C2C 自由市场（类似闲鱼）
2. 官方回收/验机（转转官方给出的回收价）

官方回收价是确定性的（按机型+成色+配件查表），这是套利的关键锚点。
H5 版: m.zhuanzhuan.com

策略：
1. 搜索获取 C2C 挂牌价
2. 通过回收估价页面获取官方回收价
3. 对比两个价格体系
"""

from __future__ import annotations

from datetime import datetime, timezone

from jev_mas.models import Platform, ProductListing
from jev_mas.scrapers.base import BaseScraper


class ZhuanzhuanScraper(BaseScraper):
    platform = Platform.ZHUANZHUAN
    BASE_URL = "https://m.zhuanzhuan.com"

    async def search(self, keyword: str, max_results: int = 20) -> list[ProductListing]:
        page = await self.new_page()
        try:
            await page.goto(
                f"{self.BASE_URL}/search/list/?keyword={keyword}",
                wait_until="networkidle",
            )
            await page.wait_for_timeout(2000)

            items = await page.query_selector_all('[class*="item"], [class*="card"], [class*="product"]')
            listings: list[ProductListing] = []

            for item in items[:max_results]:
                try:
                    title_el = await item.query_selector('[class*="title"], [class*="name"]')
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
        page = await self.new_page()
        try:
            await page.goto(f"{self.BASE_URL}/huishou/", wait_until="networkidle")
            search_input = await page.query_selector('input[type="search"], input[type="text"]')
            if not search_input:
                return None

            await search_input.fill(model_name)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)

            price_el = await page.query_selector('[class*="price"], [class*="estimate"]')
            if not price_el:
                return None

            price_text = (await price_el.inner_text()).strip()
            price = float("".join(c for c in price_text if c.isdigit() or c == ".") or "0")
            return price if price > 0 else None
        except Exception:
            return None
        finally:
            await page.close()
