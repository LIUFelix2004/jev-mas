"""拍机堂爬虫 —— 回收价参考源

在本系统中拍机堂只做"卖出端"：闲鱼/转转找货，拍机堂估价页给出
按成色分档的回收价（99新/95新/9新/85新/8新），作为套利的退出价。

估价详情页结构（来自 App 截图）:
    苹果 iPhone 16 256G 白色 大陆国行 保修时长<30天
    今日参考价 ¥3,850
    99新 3850元 | 95新 3750元 | 9新 3680元 | 85新 3330元 | 8新 3210元

页面 class 名不可靠，解析全部基于 innerText + 正则，与 DOM 结构解耦。
默认 PC 站 www.paijitang.com，可用 PAIJITANG_URL 环境变量覆盖；接口尚未实测，
先跑 probe_paijitang.py 录下真实接口，再补 API 直连策略。
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.async_api import Page

from jev_mas.models import GRADE_TO_CONDITION, Condition, Platform, ProductListing, RecyclePrice
from jev_mas.scrapers.base import BaseScraper

GRADE_RE = re.compile(r"(?<!\d)(\d{1,2}新)\s*[¥￥]?\s*([\d,]+(?:\.\d+)?)\s*元")
REF_PRICE_RE = re.compile(r"今日参考价\s*[¥￥]?\s*([\d,]+(?:\.\d+)?)")
STORAGE_RE = re.compile(r"(?<![\w])(\d+(?:G|T|GB|TB))(?![\w])", re.IGNORECASE)
CHANNEL_KEYWORDS = ("国行", "港澳台", "展示机", "官换机", "资源机", "美版", "日版", "韩版", "海外")
BRAND_PREFIXES = ("苹果", "华为", "小米", "荣耀", "三星", "一加", "魅族", "联想", "索尼", "努比亚", "锤子", "乐视", "金立")

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def context_options(url: str) -> dict:
    """m. 开头的 H5 站用手机模拟，其余按 PC 站处理"""
    if urlparse(url).hostname.startswith("m."):
        return {"viewport": {"width": 430, "height": 932}, "user_agent": MOBILE_UA, "is_mobile": True, "has_touch": True}
    return {"viewport": {"width": 1440, "height": 900}, "user_agent": DESKTOP_UA}


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def _strip_brand(name: str) -> str:
    for b in BRAND_PREFIXES:
        if name.startswith(b + " "):
            return name[len(b) + 1:].strip()
    return name.strip()


def parse_spec_line(line: str) -> dict[str, str]:
    """'苹果 iPhone 16 256G 白色 大陆国行 保修时长<30天' → 型号/容量/颜色/渠道/保修"""
    m = STORAGE_RE.search(line)
    if not m:
        return {}
    info = {"model_name": _strip_brand(line[: m.start()]), "storage": m.group(1).upper().replace("GB", "G").replace("TB", "T")}
    colors = []
    for tok in line[m.end():].split():
        if tok.startswith("保修"):
            info["warranty"] = tok
        elif any(k in tok for k in CHANNEL_KEYWORDS):
            info["channel"] = tok
        else:
            colors.append(tok)
    if colors:
        info["color"] = " ".join(colors)
    return info


def parse_price_sheet(text: str) -> RecyclePrice | None:
    """从估价详情页的 innerText 解析出分档回收价"""
    grades: dict[str, float] = {}
    for grade, price in GRADE_RE.findall(text):
        grades.setdefault(grade, _to_float(price))
    if not grades:
        return None

    spec_line = ""
    spec: dict[str, str] = {}
    for line in (l.strip() for l in text.splitlines()):
        if STORAGE_RE.search(line) and (spec := parse_spec_line(line)) and spec.get("model_name"):
            spec_line = line
            break

    ref = REF_PRICE_RE.search(text)
    return RecyclePrice(
        model_name=spec.get("model_name", ""),
        spec=spec_line,
        reference_price=_to_float(ref.group(1)) if ref else max(grades.values()),
        grade_prices=grades,
        storage=spec.get("storage", ""),
        channel=spec.get("channel", ""),
        color=spec.get("color", ""),
        warranty=spec.get("warranty", ""),
        scraped_at=datetime.now(timezone.utc),
    )


def parse_hot_models(text: str) -> list[str]:
    """机型列表页里带 🔥热 标记的型号"""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    hot: list[str] = []
    for i, line in enumerate(lines):
        name = ""
        if line in ("热", "🔥热") and i > 0:
            name = lines[i - 1]
        elif line.endswith("热") and len(line) > 2:
            name = line.rstrip("热").rstrip("🔥").strip()
        if name and (name := _strip_brand(name)) and name not in hot:
            hot.append(name)
    return hot


class PaijitangScraper(BaseScraper):
    platform = Platform.PAIJITANG
    BASE_URL = os.getenv("PAIJITANG_URL", "https://www.paijitang.com")

    async def start(self) -> None:
        await super().start()
        await self._context.close()
        opts = context_options(self.BASE_URL)
        if self._storage_state_path and os.path.exists(self._storage_state_path):
            opts["storage_state"] = self._storage_state_path
        self._context = await self._browser.new_context(**opts)
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

    async def _page_text(self, page: Page) -> str:
        return await page.evaluate("() => document.body ? document.body.innerText : ''")

    async def _open_model(self, page: Page, model_name: str) -> None:
        """首页 → 去估价 → 搜索型号 → 点第一个匹配项"""
        await page.goto(self.BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.get_by_text("去估价").first.click()
        await page.wait_for_timeout(1500)
        box = page.get_by_placeholder("请输入品牌型号")
        await box.click()
        await box.fill(model_name)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2000)
        await page.get_by_text(re.compile(re.escape(model_name), re.IGNORECASE)).first.click()
        await page.wait_for_timeout(2500)

    async def get_price_sheet(self, model_name: str) -> RecyclePrice | None:
        page = await self.new_page()
        try:
            await self._open_model(page, model_name)
            return parse_price_sheet(await self._page_text(page))
        finally:
            await page.close()

    async def get_hot_models(self) -> list[str]:
        page = await self.new_page()
        try:
            await page.goto(self.BASE_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await page.get_by_text("去估价").first.click()
            await page.wait_for_timeout(2500)
            return parse_hot_models(await self._page_text(page))
        finally:
            await page.close()

    async def get_recycle_price(self, model_name: str, condition: str) -> float | None:
        sheet = await self.get_price_sheet(model_name)
        if not sheet:
            return None
        return sheet.price_for(Condition(condition))

    async def search(self, keyword: str, max_results: int = 20) -> list[ProductListing]:
        """把估价页的每个成色档转成一条卖出端 listing，供套利引擎对比"""
        sheet = await self.get_price_sheet(keyword)
        if not sheet:
            return []
        return [
            ProductListing(
                platform=self.platform,
                title=f"{sheet.spec} {grade}",
                price=price,
                url=self.BASE_URL,
                model_name=sheet.model_name,
                condition=GRADE_TO_CONDITION.get(grade, Condition.POOR),
                storage=sheet.storage,
                color=sheet.color,
                scraped_at=sheet.scraped_at,
                raw_data={"grade": grade, "channel": sheet.channel, "warranty": sheet.warranty},
            )
            for grade, price in list(sheet.grade_prices.items())[:max_results]
        ]
