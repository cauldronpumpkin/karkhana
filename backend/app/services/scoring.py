from __future__ import annotations

import json
import re
from datetime import datetime

from openai.types.chat import ChatCompletionMessageParam

from backend.app.repository import Score, get_repository
from backend.app.services.llm import LLMService
from backend.app.services.system_prompts import SCORING_PROMPT

SCORING_DIMENSIONS = ["tam", "competition", "feasibility", "time_to_mvp", "revenue", "uniqueness", "personal_fit"]


class ScoringService:
    def __init__(self) -> None:
        self.llm = LLMService()

    async def _get_idea(self, idea_id: str):
        idea = await get_repository().get_idea(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        return idea

    async def score_idea(self, idea_id: str) -> dict[str, dict]:
        repo = get_repository()
        idea = await self._get_idea(idea_id)
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SCORING_PROMPT},
            {"role": "user", "content": (
                f"Idea: {idea.title}\n\nDescription: {idea.description}\n\n"
                f"Score this idea on 7 dimensions (0-10): TAM (market size), Competition (blue ocean=high), "
                f"Feasibility (technical), Time-to-MVP (fast=high), Revenue (clear model=high), "
                f"Uniqueness (novel=high), Personal Fit (skills match=high). Provide rationale for each. "
                f'Return ONLY JSON: {{"dimension": {{"value": float, "rationale": "str"}}}} for each dimension.'
            )},
        ]
        response = await self.llm.chat_completion_sync(messages)
        try:
            scores_data = json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
            if not match:
                raise ValueError(f"Failed to parse LLM response as JSON: {response}")
            scores_data = json.loads(match.group(1))
        scores: dict[str, dict] = {}
        for dimension in SCORING_DIMENSIONS:
            if dimension in scores_data:
                data = scores_data[dimension]
                value = max(0.0, min(10.0, float(data.get("value", 0.0))))
                rationale = data.get("rationale", "")
                await repo.put_score(Score(idea_id=idea_id, dimension=dimension, value=value, rationale=rationale, scored_at=datetime.utcnow()))
                scores[dimension] = {"value": value, "rationale": rationale}
        return scores

    async def rescore_dimension(self, idea_id: str, dimension: str, value: float, rationale: str) -> dict:
        if dimension not in SCORING_DIMENSIONS:
            raise ValueError(f"Invalid dimension: {dimension}. Must be one of {SCORING_DIMENSIONS}")
        await self._get_idea(idea_id)
        value = max(0.0, min(10.0, value))
        await get_repository().put_score(Score(idea_id=idea_id, dimension=dimension, value=value, rationale=rationale, scored_at=datetime.utcnow()))
        return {"value": value, "rationale": rationale}

    async def get_scores(self, idea_id: str) -> list[dict]:
        await self._get_idea(idea_id)
        return [
            {"id": s.id, "dimension": s.dimension, "value": s.value, "rationale": s.rationale, "scored_at": s.scored_at.isoformat()}
            for s in await get_repository().list_scores(idea_id)
        ]

    async def get_composite_score(self, idea_id: str) -> float:
        await self._get_idea(idea_id)
        scores = await get_repository().list_scores(idea_id)
        if not scores:
            return 0.0
        return round(sum(s.value for s in scores) / len(scores), 2)

    async def compare_ideas(self, idea_ids: list[str]) -> dict:
        comparison: dict[str, dict] = {}
        repo = get_repository()
        for idea_id in idea_ids:
            idea = await self._get_idea(idea_id)
            scores = await repo.list_scores(idea_id)
            scores_dict = {s.dimension: {"value": s.value, "rationale": s.rationale} for s in scores}
            composite = round(sum(s["value"] for s in scores_dict.values()) / len(scores_dict), 2) if scores_dict else 0.0
            comparison[idea_id] = {"title": idea.title, "scores": scores_dict, "composite_score": composite}
        return comparison
