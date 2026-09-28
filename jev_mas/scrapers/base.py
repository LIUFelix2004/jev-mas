"""爬虫基类

两种数据抓取策略：
1. mtop API 拦截 (推荐): Playwright 打开页面获取登录态 → page.evaluate 调用 window.lib.mtop.request()
2. DOM 解析 (兜底): 直接解析页面元素

mtop 方式返回结构化 JSON，比 DOM 解析稳定得多。
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from jev_mas.models import Platform, ProductListing


class BaseScraper(ABC):
    platform: Platform

    def __init__(self, headless: bool = True, storage_state_path: str | None = None):
        self._headless = headless
        self._storage_state_path = storage_state_path
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self._headless)

        context_opts = {
            "viewport": {"width": 375, "height": 812},
            "user_agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        }
        if self._storage_state_path and Path(self._storage_state_path).exists():
            context_opts["storage_state"] = self._storage_state_path

        self._context = await self._browser.new_context(**context_opts)

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def save_storage_state(self, path: str) -> None:
        if self._context:
            await self._context.storage_state(path=path)

    async def new_page(self) -> Page:
        if not self._context:
            raise RuntimeError("Scraper not started. Call start() first.")
        return await self._context.new_page()

    @abstractmethod
    async def search(self, keyword: str, max_results: int = 20) -> list[ProductListing]:
        ...

    @abstractmethod
    async def get_recycle_price(self, model_name: str, condition: str) -> float | None:
        ...

    async def search_with_retry(
        self, keyword: str, max_results: int = 20, retries: int = 3
    ) -> list[ProductListing]:
        for attempt in range(retries):
            try:
                return await self.search(keyword, max_results)
            except Exception:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return []
