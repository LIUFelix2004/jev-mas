"""拍机堂爬虫

拍机堂是 B2B 为主的回收平台，有明确的回收报价体系。
也有面向 C 端的回收估价。
H5 版: m.paijitang.com

关键套利场景：
- 闲鱼低价收 → 拍机堂高价卖给回收商
- 拍机堂批发价 → 闲鱼零售价
"""

from __future__ import annotations

from datetime import datetime, timezone

from jev_mas.models import Platform, ProductListing
from jev_mas.scrapers.base import BaseScraper


class PaijitangScraper(BaseScraper):
    platform = Platform.PAIJITANG
    BASE_URL = "https://m.paijitang.com"

    async def search(self, keyword: str, max_results: int = 20) -> list[ProductListing]:
        page = await self.new_page()
        try:
            await page.goto(f"{self.BASE_URL}/search?keyword={keyword}", wait_until="networkidle")
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
            await page.goto(f"{self.BASE_URL}/estimate", wait_until="networkidle")
            search_input = await page.query_selector('input[type="search"], input[type="text"]')
            if not search_input:
                return None

            await search_input.fill(model_name)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)

            price_el = await page.query_selector('[class*="price"], [class*="estimate"], [class*="value"]')
            if not price_el:
                return None

            price_text = (await price_el.inner_text()).strip()
            price = float("".join(c for c in price_text if c.isdigit() or c == ".") or "0")
            return price if price > 0 else None
        except Exception:
            return None
        finally:
            await page.close()
