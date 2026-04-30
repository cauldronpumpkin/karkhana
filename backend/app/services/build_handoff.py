from __future__ import annotations

import json
import re
from typing import Any

from openai.types.chat import ChatCompletionMessageParam
from backend.app.models.idea import Idea
from backend.app.repository import get_repository
from backend.app.services.file_manager import FileManager
from backend.app.services.llm import LLMService
from backend.app.services.memory import MemoryService
from backend.app.services.scoring import ScoringService

BUILD_STEPS = [
    "project_setup",
    "database",
    "backend",
    "frontend",
    "integration",
    "testing",
]

BUILD_STEP_DESCRIPTIONS = {
    "project_setup": "Initialize project structure, configure tools, set up version control",
    "database": "Set up database schema, models, migrations, seed data",
    "backend": "Implement API endpoints, services, business logic, authentication",
    "frontend": "Build UI components, pages, routing, state management",
    "integration": "Connect frontend to backend, test workflows, handle errors",
    "testing": "Write and run tests, fix issues, ensure quality",
}


def _safe_repo_path() -> str:
    return "<repo-root>"


def _build_context_files(project: Any | None) -> list[str]:
    context_files = [
        "graphify-out/GRAPH_REPORT.md",
        "backend/app/services/build_handoff.py",
        "backend/app/routers/build.py",
        "backend/app/services/project_twin.py",
        "frontend/src/lib/components/ProjectTwin/ProjectTwinView.svelte",
        "frontend/src/lib/api.js",
    ]
    if project:
        context_files.extend([
            "backend/app/routers/projects.py",
            "backend/app/routers/worker.py",
        ])
    return context_files


def _codex_prompt(goal: str, context_files: list[str], constraints: list[str], deliverables: list[str], verification_commands: list[str]) -> str:
    lines = [
        f"Goal: {goal}",
        f"Repo path: {_safe_repo_path()}",
        "Context files to inspect:",
        *[f"- {path}" for path in context_files],
        "Constraints:",
        *[f"- {item}" for item in constraints],
        "Deliverables:",
        *[f"- {item}" for item in deliverables],
        "Verification commands:",
        *[f"- {cmd}" for cmd in verification_commands],
        "Run graphify update . after code changes.",
        "Final response format: concise summary, files changed, tests run, and any follow-ups.",
    ]
    return "\n".join(lines)


class BuildHandoffService:
    """Service for generating Prometheus build handoff prompts and tracking build progress."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        file_manager: FileManager | None = None,
        memory_service: MemoryService | None = None,
        scoring_service: ScoringService | None = None,
    ) -> None:
        self.llm = llm_service or LLMService()
        self.fm = file_manager or FileManager()
        self.memory = memory_service or MemoryService()
        self.scoring = scoring_service or ScoringService()

    async def _get_idea(self, idea_id: str) -> Idea:
        """Fetch and validate idea exists."""
        idea = await get_repository().get_idea(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        return idea

    def _memory_key(self, idea_id: str, suffix: str) -> str:
        """Generate a memory key for build tracking."""
        return f"build_{idea_id}_{suffix}"

    async def _collect_idea_context(self, idea: Idea) -> str:
        """Gather all available context for an idea."""
        parts: list[str] = []

        # Basic idea info
        parts.append(f"# Idea: {idea.title}")
        parts.append(f"\n## Description\n{idea.description}")
        parts.append(f"\n## Current Phase\n{idea.current_phase}")

        repo = get_repository()

        # Phase reports
        phases = ["capture", "clarify", "market_research", "competitive_analysis",
                  "monetization", "feasibility", "tech_spec", "build"]
        reports_found = []
        for phase in phases:
            report = await repo.get_report(idea.id, phase)
            if report and report.content:
                reports_found.append(f"\n## {phase.replace('_', ' ').title()} Report\n{report.content}")
        parts.extend(reports_found)

        # Research findings
        completed = await repo.list_research_tasks(idea.id, {"completed"})
        if completed:
            parts.append("\n## Research Findings")
            for item in completed:
                if item.result_content:
                    parts.append(f"\n### {item.topic or 'Research'}\n{item.result_content}")

        # Scores
        try:
            scores = await self.scoring.get_scores(idea.id)
            if scores:
                parts.append("\n## Scores")
                for s in scores:
                    parts.append(f"- **{s['dimension']}**: {s['value']}/10 — {s.get('rationale', '')}")
        except Exception:
            pass

        # Memory context
        memory_context = await self.memory.get_context_for_idea(idea.id)
        if memory_context:
            parts.append(f"\n{memory_context}")

        return "\n".join(parts)

    async def generate_prometheus_prompt(self, idea_id: str) -> dict[str, Any]:
        """Generate a comprehensive Prometheus planning prompt for the entire project."""
        idea = await self._get_idea(idea_id)
        context = await self._collect_idea_context(idea)

        system_prompt = (
            "You are an expert software architect creating a detailed project plan for Prometheus, "
            "an AI coding assistant. Your task is to generate a structured planning interview document "
            "that will guide the implementation of a software project.\n\n"
            "The output should be a comprehensive project brief that includes:\n"
            "1. Project overview and goals\n"
            "2. Tech stack recommendations with rationale\n"
            "3. Architecture overview (frontend, backend, database)\n"
            "4. Detailed implementation phases\n"
            "5. Key technical decisions and trade-offs\n"
            "6. Risk assessment and mitigation strategies\n\n"
            "Format the output as a structured markdown document ready to be used as a planning prompt."
        )

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"Here is the complete context for a project that needs to be built:\n\n"
                f"{context}\n\n"
                f"Generate a comprehensive Prometheus planning prompt based on this context. "
                f"The prompt should be detailed enough that Prometheus can use it to build "
                f"the entire project step by step."
            )},
        ]

        prompt = await self.llm.chat_completion_sync(messages)

        # Store the generated prompt in memory
        await self.memory.set_memory(
            key=self._memory_key(idea_id, "prometheus_prompt"),
            value=prompt,
            category="note",
            idea_id=idea_id,
        )

        return {
            "idea_id": idea_id,
            "prompt": prompt,
            "context_summary": {
                "title": idea.title,
                "phase": idea.current_phase,
                "reports_included": len([p for p in ["capture", "clarify", "market_research",
                                                      "competitive_analysis", "monetization",
                                                      "feasibility", "tech_spec", "build"]
                                         if await get_repository().get_report(idea.id, p)]),
            },
        }

    async def generate_step_prompts(self, idea_id: str) -> dict[str, Any]:
        """Generate step-by-step build prompts for Prometheus."""
        idea = await self._get_idea(idea_id)
        context = await self._collect_idea_context(idea)

        steps_data: list[dict[str, Any]] = []

        for i, step in enumerate(BUILD_STEPS):
            step_desc = BUILD_STEP_DESCRIPTIONS[step]
            prev_steps = BUILD_STEPS[:i]
            prev_steps_text = ", ".join(prev_steps) if prev_steps else "none (this is the first step)"

            system_prompt = (
                f"You are generating a focused implementation prompt for step '{step}' of a software project. "
                f"This step covers: {step_desc}. "
                f"Previous completed steps: {prev_steps_text}. "
                f"The prompt should be self-contained and ready to copy-paste to Prometheus. "
                f"Include specific file paths, code structure, and implementation details. "
                f"Return ONLY the prompt text, no markdown formatting or explanations."
            )

            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Project context:\n\n{context}\n\n"
                    f"Generate a detailed, self-contained implementation prompt for the "
                    f"'{step}' step: {step_desc}. "
                    f"{'This is the first step — start from scratch.' if i == 0 else f'Assume the following steps are already complete: {prev_steps_text}.'}"
                )},
            ]

            step_prompt = await self.llm.chat_completion_sync(messages)

            steps_data.append({
                "step": step,
                "order": i + 1,
                "description": step_desc,
                "prompt": step_prompt,
            })

        # Store step prompts in memory
        await self.memory.set_memory(
            key=self._memory_key(idea_id, "step_prompts"),
            value=json.dumps(steps_data, ensure_ascii=False),
            category="note",
            idea_id=idea_id,
        )

        # Initialize current step if not set
        current = await self.memory.get_memory(
            key=self._memory_key(idea_id, "current_step"),
            idea_id=idea_id,
        )
        if current is None:
            await self.memory.set_memory(
                key=self._memory_key(idea_id, "current_step"),
                value=BUILD_STEPS[0],
                category="stage",
                idea_id=idea_id,
            )

        return {
            "idea_id": idea_id,
            "steps": steps_data,
            "total_steps": len(BUILD_STEPS),
        }

    async def get_current_build_state(self, idea_id: str) -> dict[str, Any]:
        """Get the current build state including completed and remaining steps."""
        await self._get_idea(idea_id)

        # Get current step from memory
        current_mem = await self.memory.get_memory(
            key=self._memory_key(idea_id, "current_step"),
            idea_id=idea_id,
        )
        current_step = current_mem.value if current_mem else BUILD_STEPS[0]

        # Get completed steps from memory
        completed_mem = await self.memory.get_memory(
            key=self._memory_key(idea_id, "completed_steps"),
            idea_id=idea_id,
        )
        completed_steps = []
        if completed_mem:
            try:
                completed_steps = json.loads(completed_mem.value)
            except (json.JSONDecodeError, TypeError):
                completed_steps = []

        # Ensure current step is valid
        if current_step not in BUILD_STEPS:
            current_step = BUILD_STEPS[0]

        remaining_steps = [s for s in BUILD_STEPS if s not in completed_steps and s != current_step]

        # Get the current step prompt if available
        step_prompts_mem = await self.memory.get_memory(
            key=self._memory_key(idea_id, "step_prompts"),
            idea_id=idea_id,
        )
        current_prompt = ""
        if step_prompts_mem:
            try:
                steps_data = json.loads(step_prompts_mem.value)
                for step_data in steps_data:
                    if step_data.get("step") == current_step:
                        current_prompt = step_data.get("prompt", "")
                        break
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "idea_id": idea_id,
            "current_step": current_step,
            "current_step_description": BUILD_STEP_DESCRIPTIONS.get(current_step, ""),
            "current_prompt": current_prompt,
            "completed_steps": completed_steps,
            "remaining_steps": remaining_steps,
            "total_steps": len(BUILD_STEPS),
            "progress": f"{len(completed_steps)}/{len(BUILD_STEPS)}",
        }

    async def get_next_actions(self, idea_id: str) -> dict[str, Any]:
        idea = await self._get_idea(idea_id)
        project = await get_repository().get_project_twin(idea_id)
        state = await self.get_current_build_state(idea_id)
        remaining = state["remaining_steps"]
        latest_step = remaining[0] if remaining else None
        scores = []
        try:
            scores = await self.scoring.get_scores(idea.id)
        except Exception:
            scores = []

        actions: list[dict[str, Any]] = []
        context_files = _build_context_files(project)

        actions.append({
            "title": "Advance the next build step",
            "reason": f"Current step is {state['current_step']}; next up is {latest_step or 'completion' }.",
            "priority": 1,
            "suggested_owner": "local-worker",
            "codex_prompt": _codex_prompt(
                goal=f"Complete the next build step for {idea.title}",
                context_files=context_files,
                constraints=[
                    "Keep worker execution separate from the web/backend control plane.",
                    "Do not introduce a new database.",
                    "Preserve existing API compatibility unless absolutely necessary.",
                ],
                deliverables=[
                    "Implement the next build step with minimal localized changes.",
                    "Update or add tests for the step.",
                ],
                verification_commands=["python -m pytest backend/tests", "graphify update ."],
            ),
        })

        if not project:
            actions.append({
                "title": "Link the idea to a project twin",
                "reason": "No project twin is attached yet, so build coordination is limited.",
                "priority": 2,
                "suggested_owner": "backend",
            })

        if not scores:
            actions.append({
                "title": "Review scoring and research context",
                "reason": "No scored dimensions are available to prioritize the build.",
                "priority": 3,
                "suggested_owner": "product",
            })

        return {
            "idea_id": idea_id,
            "status_summary": {
                "idea_title": idea.title,
                "current_phase": idea.current_phase,
                "current_step": state["current_step"],
                "remaining_steps": remaining,
                "project_attached": bool(project),
            },
            "next_actions": actions,
        }

    async def mark_step_complete(self, idea_id: str, step: str) -> dict[str, Any]:
        """Mark a build step as complete and return the next step."""
        await self._get_idea(idea_id)

        if step not in BUILD_STEPS:
            raise ValueError(f"Invalid step: {step}. Must be one of: {BUILD_STEPS}")

        # Get current completed steps
        completed_mem = await self.memory.get_memory(
            key=self._memory_key(idea_id, "completed_steps"),
            idea_id=idea_id,
        )
        completed_steps = []
        if completed_mem:
            try:
                completed_steps = json.loads(completed_mem.value)
            except (json.JSONDecodeError, TypeError):
                completed_steps = []

        if step not in completed_steps:
            completed_steps.append(step)

        # Update completed steps in memory
        await self.memory.set_memory(
            key=self._memory_key(idea_id, "completed_steps"),
            value=json.dumps(completed_steps),
            category="note",
            idea_id=idea_id,
        )

        # Determine next step
        remaining = [s for s in BUILD_STEPS if s not in completed_steps]
        next_step = remaining[0] if remaining else None

        # Update current step
        if next_step:
            await self.memory.set_memory(
                key=self._memory_key(idea_id, "current_step"),
                value=next_step,
                category="stage",
                idea_id=idea_id,
            )

        # Get next step prompt if available
        next_prompt = ""
        if next_step:
            step_prompts_mem = await self.memory.get_memory(
                key=self._memory_key(idea_id, "step_prompts"),
                idea_id=idea_id,
            )
            if step_prompts_mem:
                try:
                    steps_data = json.loads(step_prompts_mem.value)
                    for step_data in steps_data:
                        if step_data.get("step") == next_step:
                            next_prompt = step_data.get("prompt", "")
                            break
                except (json.JSONDecodeError, TypeError):
                    pass

        return {
            "idea_id": idea_id,
            "completed_step": step,
            "completed_steps": completed_steps,
            "next_step": next_step,
            "next_step_description": BUILD_STEP_DESCRIPTIONS.get(next_step, "") if next_step else "",
            "next_prompt": next_prompt,
            "is_complete": next_step is None,
        }
