"""闲鱼 (Goofish) 爬虫

两种抓取策略，按优先级尝试：

策略 1 - mtop API (推荐):
  打开 goofish.com 页面获取登录态和 mtop SDK → 通过 page.evaluate 调用
  window.lib.mtop.request() 搜索接口 → 返回结构化 JSON

  搜索接口: mtop.taobao.idlemtopsearch.pc.search
  详情接口: mtop.taobao.idle.pc.detail

策略 2 - 网络拦截 (兜底):
  监听页面的 XHR 请求，拦截搜索 API 的响应 → 解析 JSON

策略 3 - DOM 解析 (最后手段):
  直接解析页面元素，不稳定但不依赖 mtop SDK

首次使用需要手动登录（扫码），之后保存 storage_state 复用登录态。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

from playwright.async_api import Page, Response

from jev_mas.models import Platform, ProductListing
from jev_mas.scrapers.base import BaseScraper

MTOP_SEARCH_API = "mtop.taobao.idlemtopsearch.pc.search"
MTOP_DETAIL_API = "mtop.taobao.idle.pc.detail"


class XianyuScraper(BaseScraper):
    platform = Platform.XIANYU
    BASE_URL = "https://www.goofish.com"
    H5_URL = "https://m.goofish.com"

    async def _ensure_page_ready(self, page: Page) -> None:
        """打开闲鱼首页，确保 mtop SDK 加载完成"""
        await page.goto(self.BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

    async def _search_via_mtop(self, page: Page, keyword: str, max_results: int) -> list[ProductListing]:
        """策略 1: 通过 mtop SDK 直接调用搜索 API"""
        result = await page.evaluate("""
            (args) => {
                return new Promise((resolve, reject) => {
                    if (!window.lib || !window.lib.mtop || !window.lib.mtop.request) {
                        reject('mtop SDK not available');
                        return;
                    }
                    window.lib.mtop.request({
                        api: args.api,
                        v: '1.0',
                        data: {
                            keyword: args.keyword,
                            pageNumber: '1',
                            pageSize: String(args.maxResults),
                        },
                        type: 'GET',
                        dataType: 'json',
                        timeout: 10000,
                    }, (result) => {
                        resolve(JSON.stringify(result));
                    }, (error) => {
                        reject(JSON.stringify(error));
                    });
                });
            }
        """, {"api": MTOP_SEARCH_API, "keyword": keyword, "maxResults": max_results})

        data = json.loads(result) if isinstance(result, str) else result
        return self._parse_mtop_search_result(data)

    async def _search_via_intercept(self, page: Page, keyword: str, max_results: int) -> list[ProductListing]:
        """策略 2: 拦截搜索页面的 XHR 响应"""
        captured_data: list[dict] = []

        async def handle_response(response: Response) -> None:
            url = response.url
            if "mtop.taobao.idle" in url and "search" in url:
                try:
                    body = await response.json()
                    captured_data.append(body)
                except Exception:
                    pass

        page.on("response", handle_response)

        search_url = f"{self.BASE_URL}/search?q={quote(keyword)}"
        await page.goto(search_url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # 滚动触发加载更多
        for _ in range(2):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(1000)

        page.remove_listener("response", handle_response)

        listings: list[ProductListing] = []
        for data in captured_data:
            listings.extend(self._parse_mtop_search_result(data))
        return listings[:max_results]

    async def _search_via_dom(self, page: Page, keyword: str, max_results: int) -> list[ProductListing]:
        """策略 3: DOM 解析"""
        search_url = f"{self.BASE_URL}/search?q={quote(keyword)}"
        await page.goto(search_url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        for _ in range(2):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(1000)

        items_data = await page.evaluate("""
            () => {
                const results = [];
                // 尝试多种可能的选择器
                const selectors = [
                    '[class*="feeds"] [class*="item"]',
                    '[class*="card"][class*="item"]',
                    '[data-spm*="search"] a[href*="/item/"]',
                    'a[href*="/item/"]',
                ];
                let items = [];
                for (const sel of selectors) {
                    items = document.querySelectorAll(sel);
                    if (items.length > 0) break;
                }
                items.forEach(item => {
                    try {
                        const titleEl = item.querySelector('[class*="title"], [class*="name"], h3, h4');
                        const priceEl = item.querySelector('[class*="price"], [class*="Price"]');
                        const linkEl = item.closest('a[href]') || item.querySelector('a[href]');
                        if (titleEl && priceEl) {
                            const priceText = priceEl.innerText.replace(/[^0-9.]/g, '');
                            results.push({
                                title: titleEl.innerText.trim(),
                                price: parseFloat(priceText) || 0,
                                url: linkEl ? linkEl.href : '',
                            });
                        }
                    } catch(e) {}
                });
                return results;
            }
        """)

        listings: list[ProductListing] = []
        for item in (items_data or [])[:max_results]:
            price = item.get("price", 0)
            if price <= 0:
                continue
            listings.append(ProductListing(
                platform=self.platform,
                title=item.get("title", ""),
                price=price,
                url=item.get("url", ""),
                scraped_at=datetime.now(timezone.utc),
            ))
        return listings

    async def search(self, keyword: str, max_results: int = 20) -> list[ProductListing]:
        page = await self.new_page()
        try:
            await self._ensure_page_ready(page)

            # 按优先级尝试三种策略
            for strategy_name, strategy_fn in [
                ("mtop", self._search_via_mtop),
                ("intercept", self._search_via_intercept),
                ("dom", self._search_via_dom),
            ]:
                try:
                    results = await strategy_fn(page, keyword, max_results)
                    if results:
                        return results
                except Exception:
                    continue

            return []
        finally:
            await page.close()

    async def get_recycle_price(self, model_name: str, condition: str) -> float | None:
        return None

    def _parse_mtop_search_result(self, data: dict) -> list[ProductListing]:
        """解析 mtop 搜索结果 JSON"""
        listings: list[ProductListing] = []

        # mtop 响应结构: data.data.resultList 或 data.resultList
        result_list = []
        if isinstance(data, dict):
            d = data.get("data", data)
            if isinstance(d, dict):
                d = d.get("data", d)
            if isinstance(d, dict):
                result_list = d.get("resultList", d.get("itemList", d.get("items", [])))

        for item in result_list:
            try:
                main = item.get("main", item)
                title = (
                    main.get("title", "")
                    or main.get("itemTitle", "")
                    or item.get("title", "")
                )
                # 清理标题中的 HTML 标签
                title = re.sub(r"<[^>]+>", "", title).strip()

                price_str = (
                    main.get("soldPrice", "")
                    or main.get("price", "")
                    or item.get("soldPrice", "")
                    or item.get("price", "")
                )
                price = float(re.sub(r"[^\d.]", "", str(price_str)) or "0")
                if price <= 0:
                    continue

                item_id = (
                    main.get("itemId", "")
                    or item.get("itemId", "")
                    or item.get("id", "")
                )
                url = f"{self.BASE_URL}/item/{item_id}" if item_id else ""

                listings.append(ProductListing(
                    platform=self.platform,
                    title=title,
                    price=price,
                    url=url,
                    scraped_at=datetime.now(timezone.utc),
                    raw_data=item,
                ))
            except Exception:
                continue

        return listings


async def login_interactive(storage_state_path: str = "xianyu_state.json") -> None:
    """交互式登录闲鱼（扫码），保存登录态供后续使用

    用法:
        python -c "import asyncio; from jev_mas.scrapers.xianyu import login_interactive; asyncio.run(login_interactive())"
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        )
        page = await context.new_page()
        await page.goto("https://www.goofish.com")

        print("请在浏览器中完成登录（扫码/手机号），登录成功后按 Enter...")
        input()

        await context.storage_state(path=storage_state_path)
        print(f"登录态已保存到 {storage_state_path}")

        await browser.close()
