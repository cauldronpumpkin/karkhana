"""Architect Agent - defines tech stack and file structure."""

import asyncio
from typing import Any

from src.agents.base import BaseAgent
from src.utils.prompts import ARCHITECT_SYSTEM_PROMPT, ARCHITECT_USER_PROMPT, with_thinking_modules
from src.utils.parser import extract_json, extract_tag_block


class ArchitectAgent(BaseAgent):
    """Software Architect agent that defines tech stack and file tree."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.5

    def generate_coordination_requests(self, *, prd: dict[str, Any], architecture: dict[str, Any]) -> list[dict[str, Any]]:
        """Emit architecture consistency requests when constraints are ambiguous."""
        _ = prd
        file_tree = architecture.get("file_tree", {}) if isinstance(architecture, dict) else {}
        if not file_tree:
            return [
                {
                    "from_agent": "architect_agent",
                    "message_type": "clarification_request",
                    "topic": "architecture_missing_file_tree",
                    "blocking": True,
                    "content_json": {
                        "area": "architecture",
                        "question": "Generated architecture lacks a file tree.",
                    },
                }
            ]
        return []

    async def generate_architecture(
        self,
        prd: dict[str, Any],
        *,
        candidate_id: int | None = None,
        thinking_modules_enabled: bool = False,
    ) -> dict[str, Any]:
        """Generate architecture based on PRD."""
        prd_content = f"""
Title: {prd.get('title', 'N/A')}
Problem: {prd.get('problem_statement', 'N/A')}
Features: {prd.get('core_features', [])}
Constraints: {prd.get('technical_constraints', [])}
"""
        candidate_hint = ""
        if candidate_id is not None:
            candidate_hint = (
                f"\nCandidate #{candidate_id} exploration:\n"
                "- Prefer a meaningfully different architecture style and trade-off profile.\n"
                "- Include candidate metadata in JSON under `candidate_meta` with rationale, risks, assumptions, and edge_cases."
            )
        system_prompt = ARCHITECT_SYSTEM_PROMPT
        if thinking_modules_enabled:
            system_prompt = with_thinking_modules(system_prompt, "json_output")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": ARCHITECT_USER_PROMPT.format(prd_content=prd_content) + candidate_hint,
            },
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        thinking = extract_tag_block(response, "thinking")
        architecture = extract_json(response) or {}
        if thinking:
            architecture["thinking"] = thinking[:12000]
        if candidate_id is not None:
            architecture.setdefault("candidate_meta", {})
            if isinstance(architecture["candidate_meta"], dict):
                architecture["candidate_meta"].setdefault("candidate_id", candidate_id)
        return architecture

    async def generate_architecture_candidates(
        self,
        prd: dict[str, Any],
        *,
        count: int,
        parallel: bool,
        thinking_modules_enabled: bool,
    ) -> list[dict[str, Any]]:
        """Generate multiple architecture candidates for ToT exploration."""
        count = max(1, int(count))
        if count == 1:
            single = await self.generate_architecture(
                prd,
                candidate_id=1,
                thinking_modules_enabled=thinking_modules_enabled,
            )
            return [single]

        if parallel:
            tasks = [
                self.generate_architecture(
                    prd,
                    candidate_id=idx + 1,
                    thinking_modules_enabled=thinking_modules_enabled,
                )
                for idx in range(count)
            ]
            return await asyncio.gather(*tasks)

        out: list[dict[str, Any]] = []
        for idx in range(count):
            out.append(
                await self.generate_architecture(
                    prd,
                    candidate_id=idx + 1,
                    thinking_modules_enabled=thinking_modules_enabled,
                )
            )
        return out
