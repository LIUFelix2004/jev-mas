"""mitmproxy 插件：记录拍机堂 App 的 JSON 接口到 paijitang_capture/app_requests.jsonl

用法:
    pip install mitmproxy
    mitmdump -s capture_app.py --listen-port 8080

iPhone 设置（和电脑连同一个 Wi-Fi）:
    1. 设置 → 无线局域网 → 当前 Wi-Fi 的 (i) → 配置代理 → 手动：服务器填电脑 IP，端口 8080
    2. Safari 打开 http://mitm.it → 下载 iOS 证书
    3. 设置 → 通用 → VPN与设备管理 → 安装刚下载的描述文件
    4. 设置 → 通用 → 关于本机 → 证书信任设置 → 打开 mitmproxy 的开关
    5. 打开拍机堂 App → 估个价 → 选型号 → 进估价详情页
用完记得把 Wi-Fi 代理改回「关闭」，并删除 mitmproxy 描述文件。
"""

import json
from pathlib import Path

from mitmproxy import http

OUT = Path("paijitang_capture")
OUT.mkdir(exist_ok=True)
LOG = OUT / "app_requests.jsonl"
HOST_KEYWORDS = ("paijitang", "aihuishou")


def response(flow: http.HTTPFlow) -> None:
    if not any(k in flow.request.pretty_host for k in HOST_KEYWORDS):
        return
    if "json" not in flow.response.headers.get("content-type", ""):
        return
    try:
        body = json.loads(flow.response.get_text())
    except Exception:
        return
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "url": flow.request.pretty_url,
            "method": flow.request.method,
            "post_data": flow.request.get_text(),
            "status": flow.response.status_code,
            "body": body,
        }, ensure_ascii=False) + "\n")
    print(f"[记录] {flow.request.method} {flow.request.pretty_url[:120]}")
