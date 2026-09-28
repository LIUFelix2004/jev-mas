"""Jev (TypeSafe System One) API 客户端

端点: POST https://api.typesafe.ai/v1/systemone
认证: Authorization: Bearer <apikey_...>
模型: jev-latest

请求体:
{
  "state": "上下文文本",
  "model": "jev-latest",
  "questions": {
    "q1": { "type": "noul", "instructions": "..." },
    "q2": { "type": "choice", "instructions": "...", "criteria": {"a": "desc", "b": "desc"} },
    "q3": { "type": "score", "instructions": "...", "criteria": ["低", "中", "高"] }
  }
}

响应体:
{
  "model": "jev-1.13.0",
  "answers": {
    "q1": { "type": "noul", "noul": 0.98 },
    "q2": { "type": "choice", "choice": "a", "confidence": 0.78, "probabilities": {"a": 0.85, "b": 0.15} },
    "q3": { "type": "score", "score": 1.0, "confidence": 1.0, "legend": {...}, "probabilities": {...} }
  },
  "usage": { "input_tokens": 296, "output_tokens": 20 }
}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class NoulAnswer:
    noul: float = 0.0
    raw: dict | None = None


@dataclass
class ChoiceAnswer:
    choice: str = ""
    confidence: float = 0.0
    probabilities: dict[str, float] = field(default_factory=dict)
    raw: dict | None = None


@dataclass
class ScoreAnswer:
    score: float = 0.0
    confidence: float = 0.0
    legend: dict[str, str] = field(default_factory=dict)
    probabilities: dict[str, float] = field(default_factory=dict)
    raw: dict | None = None


@dataclass
class JevResponse:
    model: str = ""
    answers: dict[str, NoulAnswer | ChoiceAnswer | ScoreAnswer] = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict | None = None


class JevClient:
    def __init__(self, api_key: str, base_url: str = "https://api.typesafe.ai", model: str = "jev-latest"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
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
            "/v1/systemone",
            json={"state": state, "model": self._model, "questions": questions},
        )
        resp.raise_for_status()
        data = resp.json()

        response = JevResponse(
            model=data.get("model", ""),
            raw=data,
        )
        usage = data.get("usage", {})
        response.input_tokens = usage.get("input_tokens", 0)
        response.output_tokens = usage.get("output_tokens", 0)

        for qid, ans in data.get("answers", {}).items():
            ans_type = ans.get("type", "")
            if ans_type == "noul":
                response.answers[qid] = NoulAnswer(noul=ans.get("noul", 0.0), raw=ans)
            elif ans_type == "choice":
                response.answers[qid] = ChoiceAnswer(
                    choice=ans.get("choice", ""),
                    confidence=ans.get("confidence", 0.0),
                    probabilities=ans.get("probabilities", {}),
                    raw=ans,
                )
            elif ans_type == "score":
                response.answers[qid] = ScoreAnswer(
                    score=ans.get("score", 0.0),
                    confidence=ans.get("confidence", 0.0),
                    legend=ans.get("legend", {}),
                    probabilities=ans.get("probabilities", {}),
                    raw=ans,
                )

        return response

    async def noul(self, state: str, instructions: str, question_id: str = "q") -> NoulAnswer:
        resp = await self._call(state, {
            question_id: {"type": "noul", "instructions": instructions},
        })
        ans = resp.answers.get(question_id)
        return ans if isinstance(ans, NoulAnswer) else NoulAnswer()

    async def choice(
        self, state: str, instructions: str, criteria: dict[str, str], question_id: str = "q"
    ) -> ChoiceAnswer:
        resp = await self._call(state, {
            question_id: {"type": "choice", "instructions": instructions, "criteria": criteria},
        })
        ans = resp.answers.get(question_id)
        return ans if isinstance(ans, ChoiceAnswer) else ChoiceAnswer()

    async def score(
        self, state: str, instructions: str, criteria: list[str], question_id: str = "q"
    ) -> ScoreAnswer:
        resp = await self._call(state, {
            question_id: {"type": "score", "instructions": instructions, "criteria": criteria},
        })
        ans = resp.answers.get(question_id)
        return ans if isinstance(ans, ScoreAnswer) else ScoreAnswer()

    async def multi(self, state: str, questions: dict[str, dict]) -> JevResponse:
        return await self._call(state, questions)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> JevClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
