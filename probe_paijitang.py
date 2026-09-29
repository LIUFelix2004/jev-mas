"""拍机堂探测工具：手动操作浏览器，自动录下接口并试解析当前页面

用法:
    python probe_paijitang.py                      # 默认打开 m.paijitang.com
    python probe_paijitang.py --url https://xxx    # 换成你实际能打开的 H5 地址

在弹出的 Chrome 里登录、进入「估个价」→ 选一个型号 → 打开估价详情页。
回到终端:
    回车   解析当前页面（成色分档价 / 热门机型），并保存接口记录
    q 回车 保存并退出

输出:
    paijitang_capture/requests.jsonl   每条 JSON 接口的 url/方法/请求体/响应
    paijitang_capture/page_N.txt       每次回车时的页面文本
    paijitang_state.json               登录态（下次自动复用）
这些文件含登录信息，已加入 .gitignore，不要提交或外发。
"""

import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import Response, async_playwright
from rich.console import Console
from rich.table import Table

from jev_mas.scrapers.paijitang import MOBILE_UA, parse_hot_models, parse_price_sheet

console = Console()
OUT = Path("paijitang_capture")
STATE = "paijitang_state.json"
SKIP_EXT = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".woff", ".woff2", ".ttf", ".ico")


async def main(url: str) -> None:
    OUT.mkdir(exist_ok=True)
    log = (OUT / "requests.jsonl").open("a", encoding="utf-8")
    seen = 0

    async def on_response(resp: Response) -> None:
        nonlocal seen
        req = resp.request
        if req.resource_type not in ("xhr", "fetch") or resp.url.split("?")[0].endswith(SKIP_EXT):
            return
        try:
            body = await resp.json()
        except Exception:
            return
        seen += 1
        log.write(json.dumps({
            "url": resp.url,
            "method": req.method,
            "post_data": req.post_data,
            "status": resp.status,
            "body": body,
        }, ensure_ascii=False) + "\n")
        log.flush()
        console.print(f"[dim]  [{seen}] {req.method} {resp.url[:110]}[/]")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False, channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-first-run"],
        )
        opts = {"viewport": {"width": 430, "height": 932}, "user_agent": MOBILE_UA, "is_mobile": True, "has_touch": True}
        if Path(STATE).exists():
            opts["storage_state"] = STATE
            console.print("[green]已加载上次的登录态[/]")
        ctx = await browser.new_context(**opts)
        await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        ctx.on("response", on_response)

        page = await ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
        except Exception as e:
            console.print(f"[yellow]打开 {url} 失败: {e}\n可以在浏览器地址栏手动输入正确地址[/]")

        n = 0
        while True:
            cmd = await asyncio.to_thread(input, "\n[回车=解析当前页 / q=退出] ")
            page = ctx.pages[-1]
            n += 1
            text = await page.evaluate("() => document.body ? document.body.innerText : ''")
            (OUT / f"page_{n}.txt").write_text(f"URL: {page.url}\n\n{text}", encoding="utf-8")
            await ctx.storage_state(path=STATE)
            console.print(f"当前页: {page.url}  (文本已存 page_{n}.txt，已录 {seen} 条接口)")

            sheet = parse_price_sheet(text)
            if sheet:
                t = Table(title=f"{sheet.spec or sheet.model_name}  参考价 ¥{sheet.reference_price:.0f}")
                t.add_column("成色")
                t.add_column("回收价", justify="right", style="green")
                for g, p in sheet.grade_prices.items():
                    t.add_row(g, f"¥{p:.0f}")
                console.print(t)
                console.print(f"型号={sheet.model_name!r} 容量={sheet.storage!r} 颜色={sheet.color!r} "
                              f"渠道={sheet.channel!r} 保修={sheet.warranty!r}")
            hot = parse_hot_models(text)
            if hot:
                console.print(f"[red]热门机型[/]: {', '.join(hot)}")
            if not sheet and not hot:
                console.print("[yellow]这一页没解析出估价或热门机型[/]")

            if cmd.strip().lower() == "q":
                break

        log.close()
        await browser.close()
        console.print(f"\n完成。把 {OUT}/requests.jsonl 里跟估价相关的几条（去掉 token/cookie）发给我即可接 API 直连。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://m.paijitang.com")
    asyncio.run(main(ap.parse_args().url))
