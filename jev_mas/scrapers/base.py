"""爬虫基类

使用系统已安装的 Chrome 浏览器 (channel="chrome") 而非 Playwright 自带的 Chromium，
绕过阿里系的反自动化检测。
"""

from __future__ import annotations

import asyncio
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
        # 用系统 Chrome 而非 Playwright Chromium，降低被反爬检测的概率
        self._browser = await self._pw.chromium.launch(
            headless=self._headless,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        context_opts = {
            "viewport": {"width": 430, "height": 932},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }
        if self._storage_state_path and Path(self._storage_state_path).exists():
            context_opts["storage_state"] = self._storage_state_path

        self._context = await self._browser.new_context(**context_opts)

        # 注入反检测脚本
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            delete navigator.__proto__.webdriver;
        """)

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
