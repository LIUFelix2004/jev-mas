"""Jev (TypeSafe System One) API 客户端

实际 API 格式：
- 端点: POST {base_url}/v1/decisions
- 认证: Authorization: Bearer <TYPESAFE_API_KEY>
- 请求体: { "state": "上下文", "questions": { "id": { "type": "noul|choice|score", ... } } }
- 响应体: { "answers": { "id": { "type": "...", "confidence": 0.95, ... } } }

三种判断类型：
- Noul: 是/否判断，返回 0-1 概率
- Choice: 从选项中选择，返回各选项概率
- Score: 按量表打分，返回加权分数
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class JevAnswer:
    question_id: str
    answer_type: str
    confidence: float = 0.0
    # noul
    yes_probability: float | None = None
    # choice
    selected: str | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    # score
    score_value: float | None = None
    level: str | None = None
    raw: dict | None = None


@dataclass
class JevResponse:
    answers: dict[str, JevAnswer] = field(default_factory=dict)
    raw: dict | None = None


class JevClient:
    def __init__(self, api_key: str, base_url: str = "https://api.typesafe.ai"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

    async def _call(self, state: str, questions: dict[str, dict]) -> JevResponse:
        resp = await self._http.post(
            "/v1/decisions",
            json={"state": state, "questions": questions},
        )
        resp.raise_for_status()
        data = resp.json()

        response = JevResponse(raw=data)
        for qid, ans in data.get("answers", {}).items():
            answer = JevAnswer(
                question_id=qid,
                answer_type=ans.get("type", ""),
                confidence=ans.get("confidence", 0.0),
                raw=ans,
            )
            if ans.get("type") == "noul":
                probs = ans.get("probabilities", {})
                answer.yes_probability = probs.get("yes", probs.get("true", 0.0))
            elif ans.get("type") == "choice":
                answer.probabilities = ans.get("probabilities", {})
                if answer.probabilities:
                    answer.selected = max(answer.probabilities, key=answer.probabilities.get)
            elif ans.get("type") == "score":
                answer.score_value = ans.get("score", ans.get("value", 0.0))
                answer.level = ans.get("level", "")
            response.answers[qid] = answer

        return response

    async def noul(self, state: str, question: str, question_id: str = "q") -> JevAnswer:
        resp = await self._call(state, {
            question_id: {"type": "noul", "instructions": question},
        })
        return resp.answers.get(question_id, JevAnswer(question_id=question_id, answer_type="noul"))

    async def choice(self, state: str, question: str, options: list[str], question_id: str = "q") -> JevAnswer:
        resp = await self._call(state, {
            question_id: {
                "type": "choice",
                "instructions": question,
                "criteria": {opt: opt for opt in options},
            },
        })
        return resp.answers.get(question_id, JevAnswer(question_id=question_id, answer_type="choice"))

    async def score(self, state: str, question: str, question_id: str = "q") -> JevAnswer:
        resp = await self._call(state, {
            question_id: {
                "type": "score",
                "instructions": question,
            },
        })
        return resp.answers.get(question_id, JevAnswer(question_id=question_id, answer_type="score"))

    async def multi(self, state: str, questions: dict[str, dict]) -> JevResponse:
        return await self._call(state, questions)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> JevClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
