"""捡漏提醒：终端 + Webhook（飞书/钉钉/企微 文本消息）"""

from __future__ import annotations

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jev_mas.models import CONDITION_LABELS, DEFECT_LABELS, Deal

console = Console()
RISK_LABELS = {"low": "低", "medium": "中", "high": "高"}


def _stars(x: float) -> str:
    n = max(0, min(5, round(x * 5)))
    return "★" * n + "☆" * (5 - n)


def print_deal(deal: Deal) -> None:
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column(style="bold")
    t.add_column()
    t.add_row("商品", deal.listing.title)
    t.add_row("价格", f"[green]¥{deal.listing.price:.0f}[/]  行情 ¥{deal.reference_price:.0f}（{deal.sample_size} 条样本）")
    t.add_row("低于行情", f"[bold yellow]¥{deal.discount:.0f} ({deal.discount_rate:.0%})[/]")
    t.add_row("成色/问题", f"{CONDITION_LABELS[deal.vetting.condition.value]} / {DEFECT_LABELS[deal.vetting.defect.value]}")
    t.add_row("可信度", f"{_stars(deal.confidence)}  风险 {RISK_LABELS.get(deal.risk, '?')}")
    t.add_row("链接", deal.listing.url)
    console.print(Panel(t, title=f"[bold]捡漏 · {deal.keyword}[/]", border_style="yellow"))


async def send_webhook(url: str, deal: Deal) -> None:
    if not url:
        return
    text = (
        f"[闲鱼捡漏] {deal.keyword}\n"
        f"{deal.listing.title[:60]}\n"
        f"¥{deal.listing.price:.0f}，行情 ¥{deal.reference_price:.0f}，低 ¥{deal.discount:.0f} ({deal.discount_rate:.0%})\n"
        f"成色 {CONDITION_LABELS[deal.vetting.condition.value]}，风险 {RISK_LABELS.get(deal.risk, '?')}，可信度 {deal.confidence:.0%}\n"
        f"{deal.listing.url}"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"msgtype": "text", "text": {"content": text}})
    except Exception as e:
        console.print(f"[red]Webhook 推送失败: {e}[/]")
