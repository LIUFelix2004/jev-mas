"""jev-mas 闲鱼捡漏监控

    python -m jev_mas.main           # 持续监控
    python -m jev_mas.main --once    # 只扫一轮
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console
from rich.table import Table

from jev_mas.alerts import print_deal, send_webhook
from jev_mas.config import Config
from jev_mas.db import Database
from jev_mas.deals import find_deals
from jev_mas.jev.client import JevClient
from jev_mas.jev.judge import vet_all
from jev_mas.scrapers.xianyu import XianyuScraper

console = Console()


async def scan_keyword(keyword: str, scraper: XianyuScraper, jev: JevClient, config: Config, db: Database) -> tuple:
    listings = await scraper.search_with_retry(keyword, max_results=config.max_results)
    vetted = await vet_all(jev, keyword, listings)
    history = db.price_history(keyword, config.history_days, {l.item_id for l in listings})
    db.save_items(keyword, vetted)
    deals = await find_deals(jev, keyword, vetted, history, config.min_profit, config.min_discount_rate)

    new = 0
    for d in deals:
        if d.confidence < config.min_confidence or not db.record_deal(d):
            continue
        new += 1
        print_deal(d)
        await send_webhook(config.webhook_url, d)
    valid = sum(1 for _, v in vetted if v.valid)
    return len(listings), valid, len(deals), new


async def scan_once(scraper, jev, config, db) -> None:
    summary = Table(title="本轮扫描")
    for col in ("关键词", "抓到", "合格", "低于行情", "新推送"):
        summary.add_column(col, justify="right" if col != "关键词" else "left")
    for kw in config.target_keywords:
        try:
            summary.add_row(kw, *map(str, await scan_keyword(kw, scraper, jev, config, db)))
        except Exception as e:
            console.print(f"[red]'{kw}' 扫描失败: {e}[/]")
    console.print(summary)


async def run(once: bool) -> None:
    config = Config()
    if not config.jev_api_key:
        console.print("[red]请在 .env 里设置 TYPESAFE_API_KEY[/]")
        sys.exit(1)

    db = Database(config.db_path)
    jev = JevClient(config.jev_api_key, config.jev_base_url)
    scraper = XianyuScraper(headless=config.headless, storage_state_path="xianyu_state.json")
    await scraper.start()

    console.print("[bold]jev-mas 闲鱼捡漏监控[/]")
    console.print(f"目标: {', '.join(config.target_keywords)}")
    console.print(f"条件: 低于行情 ≥{config.min_discount_rate:.0%} 且 ≥¥{config.min_profit:.0f}，可信度 ≥{config.min_confidence:.0%}\n")

    try:
        n = 0
        while True:
            n += 1
            console.print(f"[bold cyan]第 {n} 轮扫描...[/]")
            await scan_once(scraper, jev, config, db)
            await scraper.save_storage_state("xianyu_state.json")
            if once:
                break
            console.print(f"[dim]{config.scan_interval_minutes} 分钟后下一轮，Ctrl+C 退出[/]\n")
            await asyncio.sleep(config.scan_interval_minutes * 60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await scraper.stop()
        await jev.close()
        db.close()
        console.print("[bold]已停止[/]")


def main() -> None:
    ap = argparse.ArgumentParser(description="闲鱼捡漏监控")
    ap.add_argument("--once", action="store_true", help="只扫一轮")
    try:
        asyncio.run(run(ap.parse_args().once))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
