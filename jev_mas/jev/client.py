"""Jev API 客户端封装

Jev 提供三种核心操作：
- Choice: 从候选项中选择最佳答案
- Score: 对内容打分 (0-1)
- Classify: 将内容归入预定义类别

所有操作延迟约 80-100ms，适合高频调用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class JevResult:
    choice: str | None = None
    score: float | None = None
    category: str | None = None
    raw: dict | None = None


class JevClient:
    def __init__(self, api_key: str, base_url: str = "https://api.jev.ai"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )

    async def choice(self, query: str, options: list[str]) -> JevResult:
        resp = await self._http.post(
            "/v1/choice",
            json={"query": query, "options": options},
        )
        resp.raise_for_status()
        data = resp.json()
        return JevResult(choice=data.get("choice"), raw=data)

    async def score(self, query: str, content: str) -> JevResult:
        resp = await self._http.post(
            "/v1/score",
            json={"query": query, "content": content},
        )
        resp.raise_for_status()
        data = resp.json()
        return JevResult(score=data.get("score"), raw=data)

    async def classify(self, content: str, categories: list[str]) -> JevResult:
        resp = await self._http.post(
            "/v1/classify",
            json={"content": content, "categories": categories},
        )
        resp.raise_for_status()
        data = resp.json()
        return JevResult(category=data.get("category"), raw=data)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> JevClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
