from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from openai.types.chat import ChatCompletionMessageParam

from backend.app.repository import ResearchTask, get_repository
from backend.app.services.llm import LLMService
from backend.app.services.system_prompts import RESEARCH_INTEGRATION_PROMPT


class ResearchService:
    def __init__(self, file_manager: object | None = None, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    async def generate_research_prompts(self, idea_id: str) -> list[dict]:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        if not idea:
            raise ValueError(f"Idea {idea_id} not found")
        recent_context = "\n".join(f"{msg.role}: {msg.content}" for msg in (await repo.list_messages(idea_id))[-20:])
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": (
                "You are a research strategist. Analyze the given idea and identify specific knowledge gaps "
                "that need deep research via Gemini Deep Research. Generate 2-4 focused research prompts. "
                "Each prompt should be specific, include what we already know, and clearly state what's missing. "
                "Format each prompt for Gemini Deep Research with clear scope and expected deliverables. "
                "Return ONLY a JSON array of objects with 'topic' and 'prompt' keys. No other text."
            )},
            {"role": "user", "content": (
                f"Idea: {idea.title}\nDescription: {idea.description}\nCurrent phase: {idea.current_phase}\n\n"
                f"Recent conversation context:\n{recent_context}\n\n"
                f"Generate specific Gemini Deep Research prompts for the knowledge gaps in this idea."
            )},
        ]
        prompts = self._parse_prompts(await self.llm_service.chat_completion_sync(messages))
        tasks = []
        for item in prompts:
            task_id = await self.create_research_task(idea_id, item["prompt"], item["topic"])
            tasks.append({"topic": item["topic"], "prompt": item["prompt"], "task_id": task_id})
        return tasks

    async def create_research_task(self, idea_id: str, prompt: str, topic: str) -> str:
        repo = get_repository()
        if not await repo.get_idea(idea_id):
            raise ValueError(f"Idea {idea_id} not found")
        task = ResearchTask(id=str(uuid4()), idea_id=idea_id, prompt_text=prompt, topic=topic, status="pending")
        await repo.add_research_task(task)
        return task.id

    async def upload_research_result(self, idea_id: str, task_id: str, content: str) -> str:
        repo = get_repository()
        task = await repo.get_research_task(idea_id, task_id)
        if not task:
            raise ValueError(f"Research task {task_id} not found for idea {idea_id}")
        task.status = "completed"
        task.result_file_path = f"{task_id[:8]}-result.md"
        task.result_content = content
        task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await repo.save_research_task(task)
        return task.result_file_path

    async def integrate_research(self, idea_id: str, task_id: str) -> dict:
        task = await get_repository().get_research_task(idea_id, task_id)
        if not task:
            raise ValueError(f"Research task {task_id} not found for idea {idea_id}")
        if task.status != "completed":
            raise ValueError(f"Research task {task_id} is not completed (status: {task.status})")
        research_content = task.result_content or task.prompt_text
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": RESEARCH_INTEGRATION_PROMPT},
            {"role": "user", "content": f"Research content:\n\n{research_content}"},
        ]
        return {
            "task_id": task_id,
            "topic": task.topic or self._extract_topic(task.prompt_text),
            "summary": await self.llm_service.chat_completion_sync(messages),
        }

    async def get_pending_tasks(self, idea_id: str) -> list[dict]:
        tasks = await get_repository().list_research_tasks(idea_id, {"pending", "submitted"})
        return [self._task_to_dict(t) for t in tasks]

    async def get_completed_tasks(self, idea_id: str) -> list[dict]:
        tasks = await get_repository().list_research_tasks(idea_id, {"completed"})
        return [self._task_to_dict(t) for t in sorted(tasks, key=lambda t: t.completed_at or t.created_at, reverse=True)]

    @staticmethod
    def _parse_prompts(response: str) -> list[dict]:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(line for line in cleaned.splitlines() if not line.strip().startswith("```"))
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [{"topic": item.get("topic", "Research"), "prompt": item.get("prompt", "")} for item in data if isinstance(item, dict) and item.get("prompt")]
        return []

    @staticmethod
    def _task_to_dict(task: ResearchTask) -> dict:
        return {
            "id": task.id,
            "idea_id": task.idea_id,
            "prompt_text": task.prompt_text,
            "status": task.status,
            "result_file_path": task.result_file_path,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

    @staticmethod
    def _extract_topic(prompt_text: str) -> str:
        first_line = prompt_text.splitlines()[0].strip() if prompt_text.splitlines() else ""
        return first_line[:80] if first_line else "Research"
