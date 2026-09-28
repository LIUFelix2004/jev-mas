"""测试闲鱼爬虫

使用方式：

1. 首次登录（需要有头浏览器，扫码登录）:
   python test_xianyu.py --login

2. 测试搜索（已有登录态）:
   python test_xianyu.py "iPhone 15 Pro Max"

3. 无登录态测试（可能只能拿到部分结果）:
   python test_xianyu.py "iPhone 15 Pro Max" --no-auth
"""

import argparse
import asyncio
import sys

from rich.console import Console
from rich.table import Table

console = Console()


async def do_login():
    from jev_mas.scrapers.xianyu import login_interactive
    await login_interactive("xianyu_state.json")


async def do_search(keyword: str, use_auth: bool):
    from jev_mas.scrapers.xianyu import XianyuScraper

    storage_path = "xianyu_state.json" if use_auth else None
    scraper = XianyuScraper(headless=False, storage_state_path=storage_path)
    await scraper.start()

    try:
        console.print(f"[bold]搜索: {keyword}[/]")
        console.print(f"登录态: {'已加载' if use_auth else '未使用'}")
        console.print()

        results = await scraper.search(keyword, max_results=15)

        if not results:
            console.print("[yellow]未找到结果。可能需要先登录: python test_xianyu.py --login[/]")
            return

        table = Table(title=f"闲鱼搜索结果 ({len(results)} 条)")
        table.add_column("#", justify="right", width=3)
        table.add_column("标题", max_width=40)
        table.add_column("价格", justify="right", style="green")
        table.add_column("链接", max_width=30)

        for i, item in enumerate(results, 1):
            table.add_row(
                str(i),
                item.title[:38],
                f"¥{item.price:.0f}",
                item.url[-30:] if item.url else "",
            )

        console.print(table)

        # 保存登录态（如果登录了的话）
        if use_auth:
            await scraper.save_storage_state("xianyu_state.json")
            console.print("[dim]登录态已更新[/]")
    finally:
        await scraper.stop()


def main():
    parser = argparse.ArgumentParser(description="测试闲鱼爬虫")
    parser.add_argument("keyword", nargs="?", default="iPhone 15 Pro Max", help="搜索关键词")
    parser.add_argument("--login", action="store_true", help="交互式登录")
    parser.add_argument("--no-auth", action="store_true", help="不使用登录态")
    args = parser.parse_args()

    if args.login:
        asyncio.run(do_login())
    else:
        asyncio.run(do_search(args.keyword, use_auth=not args.no_auth))


if __name__ == "__main__":
    main()
