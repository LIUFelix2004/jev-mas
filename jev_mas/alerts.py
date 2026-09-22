"""通知推送

发现高价值套利机会时推送通知。
支持：
- 终端输出（Rich）
- Webhook（飞书/钉钉/企微）
"""

from __future__ import annotations

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jev_mas.models import ArbitrageOpportunity

console = Console()


def print_opportunity(opp: ArbitrageOpportunity) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("买入", f"[green]{opp.buy_listing.platform.value}[/] {opp.buy_listing.title}")
    table.add_row("价格", f"[green]¥{opp.buy_listing.price:.0f}[/]")
    table.add_row("卖出", f"[red]{opp.sell_listing.platform.value}[/] {opp.sell_listing.title}")
    table.add_row("价格", f"[red]¥{opp.sell_listing.price:.0f}[/]")
    table.add_row("差价", f"[bold yellow]¥{opp.price_diff:.0f} ({opp.profit_rate:.1%})[/]")
    table.add_row("可信度", f"{'★' * int(opp.confidence * 5)}{'☆' * (5 - int(opp.confidence * 5))}")

    console.print(Panel(table, title="[bold]套利机会[/]", border_style="yellow"))


async def send_webhook(url: str, opp: ArbitrageOpportunity) -> None:
    if not url:
        return
    payload = {
        "msgtype": "text",
        "text": {
            "content": (
                f"[套利提醒] {opp.buy_listing.model_name}\n"
                f"买: {opp.buy_listing.platform.value} ¥{opp.buy_listing.price:.0f}\n"
                f"卖: {opp.sell_listing.platform.value} ¥{opp.sell_listing.price:.0f}\n"
                f"差价: ¥{opp.price_diff:.0f} ({opp.profit_rate:.1%})\n"
                f"可信度: {opp.confidence:.0%}"
            ),
        },
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)
