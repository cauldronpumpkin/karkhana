"""Critic agent for multi-path architecture debate and selection."""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.utils.parser import extract_json, extract_tag_block
from src.utils.prompts import with_thinking_modules


CRITIC_SYSTEM_PROMPT = """
You are a ruthless architecture critic.
Given multiple architecture candidates, debate each option with strong trade-off analysis.
Identify hidden risks, implementation traps, maintenance costs, and edge cases.
Choose the single best candidate for actionable delivery.

Return JSON with:
{
  "winner_index": 0,
  "winner_score": 0-100,
  "summary": "...",
  "debate": [
    {
      "candidate_index": 0,
      "pros": ["..."],
      "cons": ["..."],
      "edge_cases": ["..."],
      "risks": ["..."],
      "score": 0-100
    }
  ]
}
"""


class CriticAgent(BaseAgent):
    """Selects best candidate after debating multiple architectural paths."""

    def __init__(self) -> None:
        super().__init__()
        self.temperature = 0.3

    async def debate_architecture_candidates(
        self,
        *,
        prd: dict[str, Any],
        candidates: list[dict[str, Any]],
        thinking_modules_enabled: bool = False,
    ) -> dict[str, Any]:
        system_prompt = CRITIC_SYSTEM_PROMPT
        if thinking_modules_enabled:
            system_prompt = with_thinking_modules(system_prompt, "json_output")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "PRD:\n"
                    f"{prd}\n\n"
                    "Candidates (0-indexed):\n"
                    f"{candidates}\n\n"
                    "Debate every candidate and pick one winner."
                ),
            },
        ]

        response = await self.generate(messages, temperature=self.temperature)
        report = extract_json(response) or {}
        thinking = extract_tag_block(response, "thinking")
        if thinking:
            report["thinking"] = thinking[:12000]
        if "winner_index" not in report:
            report["winner_index"] = 0
        if "winner_score" not in report:
            report["winner_score"] = 0
        if "debate" not in report or not isinstance(report.get("debate"), list):
            report["debate"] = []
        return report
