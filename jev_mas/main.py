"""jev-mas 主入口

运行流程：
1. 初始化各平台爬虫 + Jev 客户端
2. 循环：搜索 → 匹配 → 计算套利 → 推送通知
3. 终端实时看板展示结果
"""

from __future__ import annotations

import asyncio
import signal
import sys

from rich.console import Console
from rich.live import Live

from jev_mas.alerts import print_opportunity, send_webhook
from jev_mas.arbitrage import find_opportunities
from jev_mas.config import Config
from jev_mas.dashboard import build_dashboard
from jev_mas.db import Database
from jev_mas.jev.client import JevClient
from jev_mas.jev.matcher import classify_condition
from jev_mas.scrapers.paijitang import PaijitangScraper
from jev_mas.scrapers.xianyu import XianyuScraper
from jev_mas.scrapers.zhuanzhuan import ZhuanzhuanScraper

console = Console()


async def enrich_listings(jev, listings):
    for item in listings:
        if not item.condition or item.condition.value == "good":
            item.condition = await classify_condition(jev, item.title)


async def scan_once(scrapers, jev, config, db):
    listings_by_platform = {}

    for scraper in scrapers:
        platform_name = scraper.platform.value
        all_listings = []
        for keyword in config.target_categories:
            try:
                results = await scraper.search_with_retry(keyword, max_results=10)
                all_listings.extend(results)
            except Exception as e:
                console.print(f"[red]  {platform_name} 搜索 '{keyword}' 失败: {e}[/]")

        await enrich_listings(jev, all_listings)
        db.save_listings(all_listings)
        listings_by_platform[platform_name] = all_listings
        console.print(f"  [green]{platform_name}[/]: {len(all_listings)} 条结果")

    opportunities = await find_opportunities(
        listings_by_platform,
        jev,
        min_profit=config.min_profit_threshold,
    )

    for opp in opportunities:
        db.save_opportunity(opp)
        print_opportunity(opp)
        await send_webhook(config.webhook_url, opp)

    return listings_by_platform, opportunities


async def run() -> None:
    config = Config()
    if not config.jev_api_key:
        console.print("[red]请设置 JEV_API_KEY 环境变量[/]")
        sys.exit(1)

    db = Database(config.db_path)
    jev = JevClient(config.jev_api_key, config.jev_base_url)

    scrapers = [
        XianyuScraper(headless=config.headless),
        ZhuanzhuanScraper(headless=config.headless),
        PaijitangScraper(headless=config.headless),
    ]

    for s in scrapers:
        await s.start()

    console.print("[bold]jev-mas 二手数码套利监控系统[/]")
    console.print(f"监控类目: {', '.join(config.target_categories)}")
    console.print(f"最低利润阈值: ¥{config.min_profit_threshold}")
    console.print(f"扫描间隔: {config.scan_interval_minutes} 分钟")
    console.print()

    scan_count = 0
    running = True

    def handle_signal(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_signal)

    try:
        while running:
            scan_count += 1
            console.print(f"[bold cyan]第 {scan_count} 轮扫描...[/]")

            try:
                listings, opps = await scan_once(scrapers, jev, config, db)
                console.print(
                    f"  发现 [yellow]{len(opps)}[/] 个套利机会"
                    if opps
                    else "  [dim]暂未发现套利机会[/]"
                )
            except Exception as e:
                console.print(f"[red]扫描异常: {e}[/]")

            if running:
                console.print(f"[dim]等待 {config.scan_interval_minutes} 分钟后下一轮...[/]\n")
                await asyncio.sleep(config.scan_interval_minutes * 60)
    finally:
        for s in scrapers:
            await s.stop()
        await jev.close()
        db.close()
        console.print("\n[bold]已停止监控[/]")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
