"""启动一个普通的系统 Chrome（非 Playwright 启动），再通过 CDP 调试端口接入

登录/人机验证由用户在这个普通浏览器里手动完成；登录态保存在独立的
用户目录里，下次启动自动复用，不影响日常使用的 Chrome。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome() -> str:
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    for name in ("chrome", "google-chrome", "chromium"):
        if found := shutil.which(name):
            return found
    raise FileNotFoundError("找不到 Chrome，请用 CHROME_PATH 环境变量指定 chrome.exe 路径")


def cdp_ready(port: int) -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1)
        return True
    except Exception:
        return False


def launch_chrome(url: str, profile: str, port: int = 9222) -> str:
    """启动（或复用已开的）调试 Chrome，返回 CDP 地址"""
    endpoint = f"http://127.0.0.1:{port}"
    if cdp_ready(port):
        return endpoint
    chrome = os.getenv("CHROME_PATH") or find_chrome()
    subprocess.Popen([
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={Path(profile).resolve()}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ])
    for _ in range(30):
        if cdp_ready(port):
            return endpoint
        time.sleep(0.5)
    raise RuntimeError(f"Chrome 调试端口 {port} 未就绪；请先关掉所有用 {profile} 目录开的 Chrome 再试")
