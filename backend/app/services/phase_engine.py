from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from openai.types.chat import ChatCompletionMessageParam

from backend.app.repository import PhaseRecord, Report, get_repository
from backend.app.services.llm import LLMService

PHASE_ORDER = [
    "capture",
    "clarify",
    "market_research",
    "competitive_analysis",
    "monetization",
    "feasibility",
    "tech_spec",
    "build",
]

PHASE_REQUIREMENTS: dict[str, list[str]] = {
    "capture": ["Core idea description documented", "Problem statement defined", "Target audience identified"],
    "clarify": ["Detailed feature list outlined", "Value proposition articulated", "User personas defined", "Key differentiators identified"],
    "market_research": ["Total addressable market (TAM) estimated", "Market trends analyzed", "Demand signals gathered", "Target audience validated"],
    "competitive_analysis": ["Direct competitors identified", "Indirect competitors mapped", "Competitive advantages documented", "Market positioning defined"],
    "monetization": ["Revenue model selected", "Pricing strategy defined", "Unit economics estimated", "Customer acquisition cost considered"],
    "feasibility": ["Technical stack chosen", "Resource requirements estimated", "Risks identified and assessed", "Timeline projected"],
    "tech_spec": ["System architecture designed", "Core components defined", "MVP scope finalized", "Data models specified"],
    "build": ["Step-by-step build prompts generated", "MVP implementation plan ready", "Testing strategy defined"],
}

PHASE_ADVANCEMENT_PROMPT = (
    "Evaluate if this idea has enough information to advance from {current_phase} to {next_phase}. "
    "Consider: have the key questions for this phase been answered? "
    "Return JSON with ready (bool), reasoning (str), next_phase (str)."
)

PHASE_REPORT_PROMPT = (
    "Generate a comprehensive summary report for the '{phase}' phase of this idea. "
    "Include: key findings, decisions made, questions answered, and recommendations for the next phase. "
    "Format as markdown."
)


class PhaseEngine:
    def __init__(self, llm_service: LLMService | None = None, file_manager: object | None = None) -> None:
        self.llm = llm_service or LLMService()

    def get_phase_requirements(self, phase: str) -> list[str]:
        return PHASE_REQUIREMENTS.get(phase, [])

    def _get_next_phase(self, current: str) -> str | None:
        idx = PHASE_ORDER.index(current) if current in PHASE_ORDER else -1
        if idx < 0 or idx >= len(PHASE_ORDER) - 1:
            return None
        return PHASE_ORDER[idx + 1]

    async def get_current_phase(self, idea_id: str) -> str:
        idea = await get_repository().get_idea(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        return idea.current_phase

    async def suggest_advancement(self, idea_id: str) -> dict[str, Any]:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        current = idea.current_phase
        next_phase = self._get_next_phase(current)
        if next_phase is None:
            return {"ready": False, "reasoning": "Idea is already in the final phase (build). No further advancement possible.", "next_phase": current}
        recent_messages = [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in (await repo.list_messages(idea_id))[-20:]
        ]
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": PHASE_ADVANCEMENT_PROMPT.format(current_phase=current, next_phase=next_phase)},
            {"role": "user", "content": json.dumps({
                "idea_title": idea.title,
                "idea_description": idea.description,
                "current_phase": current,
                "next_phase": next_phase,
                "requirements": self.get_phase_requirements(current),
                "recent_chat": recent_messages,
            }, ensure_ascii=False)},
        ]
        response = await self.llm.chat_completion_sync(messages)
        try:
            parsed = json.loads(response)
            return {"ready": bool(parsed.get("ready", False)), "reasoning": parsed.get("reasoning", response), "next_phase": parsed.get("next_phase", next_phase)}
        except (json.JSONDecodeError, AttributeError):
            return {"ready": False, "reasoning": response, "next_phase": next_phase}

    async def approve_advancement(self, idea_id: str) -> str:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        current = idea.current_phase
        next_phase = self._get_next_phase(current)
        if next_phase is None:
            raise ValueError(f"Idea is already in the final phase: {current}")
        await self.generate_phase_report(idea_id, current)
        await repo.add_phase_record(PhaseRecord(idea_id=idea_id, phase=current, started_at=idea.created_at, completed_at=datetime.utcnow(), notes={"advanced_to": next_phase}))
        idea.current_phase = next_phase
        await repo.save_idea(idea)
        return next_phase

    async def reject_advancement(self, idea_id: str, reason: str) -> None:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        await repo.add_phase_record(PhaseRecord(idea_id=idea_id, phase=idea.current_phase, started_at=idea.created_at, completed_at=None, notes={"rejected": True, "reason": reason}))

    async def generate_phase_report(self, idea_id: str, phase: str) -> str:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        recent_messages = [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in (await repo.list_messages(idea_id))[-30:]
        ]
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": PHASE_REPORT_PROMPT.format(phase=phase)},
            {"role": "user", "content": json.dumps({
                "idea_title": idea.title,
                "idea_description": idea.description,
                "phase": phase,
                "requirements": self.get_phase_requirements(phase),
                "chat_history": recent_messages,
            }, ensure_ascii=False)},
        ]
        report = await self.llm.chat_completion_sync(messages)
        await repo.put_report(Report(idea_id=idea_id, phase=phase, title=f"{phase.replace('_', ' ').title()} Report", content=report, content_path=f"REPORT#{phase}"))
        return report
