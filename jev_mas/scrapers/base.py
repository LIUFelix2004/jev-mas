"""爬虫基类

所有平台爬虫继承此基类。使用 Playwright 做浏览器自动化。
在没有官方 API 的情况下，浏览器自动化是最稳定的方案：
- 渲染完整页面，不怕动态加载
- 可以模拟登录态
- 反爬对抗能力强（真实浏览器指纹）
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from jev_mas.models import Platform, ProductListing


class BaseScraper(ABC):
    platform: Platform

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        pw = await async_playwright().start()
        self._browser = await pw.chromium.launch(headless=self._headless)
        self._context = await self._browser.new_context(
            viewport={"width": 375, "height": 812},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        )

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()

    async def new_page(self) -> Page:
        if not self._context:
            raise RuntimeError("Scraper not started. Call start() first.")
        return await self._context.new_page()

    @abstractmethod
    async def search(self, keyword: str, max_results: int = 20) -> list[ProductListing]:
        ...

    @abstractmethod
    async def get_recycle_price(self, model_name: str, condition: str) -> float | None:
        """获取官方回收报价（转转/拍机堂）。闲鱼无此功能返回 None。"""
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
