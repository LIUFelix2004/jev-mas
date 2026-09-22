"""终端实时看板

用 Rich Live 在终端实时展示：
- 各平台最新抓取的价格
- 当前发现的套利机会
- 运行状态
"""

from __future__ import annotations

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from jev_mas.models import ArbitrageOpportunity, ProductListing

console = Console()


def build_listings_table(listings: list[ProductListing], title: str) -> Table:
    table = Table(title=title, show_lines=False)
    table.add_column("商品", max_width=30)
    table.add_column("价格", justify="right")
    table.add_column("成色")
    for item in listings[:10]:
        table.add_row(
            item.title[:28],
            f"¥{item.price:.0f}",
            item.condition.value,
        )
    return table


def build_opportunities_table(opps: list[ArbitrageOpportunity]) -> Table:
    table = Table(title="套利机会", show_lines=True)
    table.add_column("商品", max_width=20)
    table.add_column("买入", justify="right")
    table.add_column("卖出", justify="right")
    table.add_column("差价", justify="right", style="bold yellow")
    table.add_column("信度", justify="center")
    for opp in opps[:10]:
        stars = "★" * int(opp.confidence * 5) + "☆" * (5 - int(opp.confidence * 5))
        table.add_row(
            opp.buy_listing.model_name[:18] or opp.buy_listing.title[:18],
            f"[green]{opp.buy_listing.platform.value}\n¥{opp.buy_listing.price:.0f}[/]",
            f"[red]{opp.sell_listing.platform.value}\n¥{opp.sell_listing.price:.0f}[/]",
            f"¥{opp.price_diff:.0f}\n{opp.profit_rate:.1%}",
            stars,
        )
    return table


def build_dashboard(
    listings_by_platform: dict[str, list[ProductListing]],
    opportunities: list[ArbitrageOpportunity],
    scan_count: int,
    status: str = "运行中",
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )

    layout["header"].update(
        Panel(f"[bold]jev-mas 二手数码套利监控[/]  状态: {status}  扫描次数: {scan_count}")
    )

    platform_tables = []
    platform_names = {"xianyu": "闲鱼", "zhuanzhuan": "转转", "paijitang": "拍机堂"}
    for platform, items in listings_by_platform.items():
        name = platform_names.get(platform, platform)
        platform_tables.append(build_listings_table(items, f"{name} ({len(items)}条)"))

    if opportunities:
        layout["body"].split_row(
            Layout(Panel(build_opportunities_table(opportunities)), ratio=2),
            Layout(
                Panel(
                    "\n".join(
                        build_listings_table(items, platform_names.get(p, p)).__str__()
                        for p, items in list(listings_by_platform.items())[:1]
                    )
                    if listings_by_platform
                    else "暂无数据",
                ),
                ratio=1,
            ),
        )
    else:
        layout["body"].update(Panel("暂未发现套利机会，持续监控中..."))

    layout["footer"].update(Panel("[dim]Ctrl+C 退出  |  数据仅供参考，投资有风险[/]"))

    return layout
