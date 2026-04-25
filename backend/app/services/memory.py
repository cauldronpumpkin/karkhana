from __future__ import annotations

from datetime import datetime

from backend.app.repository import ProjectMemory, get_repository

VALID_CATEGORIES = {"stage", "issue", "bug", "note", "constraint", "resource"}


class MemoryService:
    """Service for managing project memory entries."""

    async def set_memory(
        self,
        key: str,
        value: str,
        category: str,
        idea_id: str | None = None,
    ) -> ProjectMemory:
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")
        repo = get_repository()
        existing = await repo.get_memory(key, idea_id)
        if existing:
            existing.value = value
            existing.category = category
            existing.updated_at = datetime.utcnow()
            return await repo.upsert_memory(existing)
        return await repo.upsert_memory(ProjectMemory(key=key, value=value, category=category, idea_id=idea_id))

    async def get_memory(self, key: str, idea_id: str | None = None) -> ProjectMemory | None:
        return await get_repository().get_memory(key, idea_id)

    async def get_all_memory(self, idea_id: str | None = None) -> list[ProjectMemory]:
        return await get_repository().list_memories(idea_id=idea_id)

    async def delete_memory(self, key: str, idea_id: str | None = None) -> bool:
        return await get_repository().delete_memory(key, idea_id)

    async def get_by_category(self, category: str, idea_id: str | None = None) -> list[ProjectMemory]:
        return await get_repository().list_memories(idea_id=idea_id, category=category)

    async def get_context_for_idea(self, idea_id: str) -> str:
        memories = await self.get_all_memory(idea_id=idea_id)
        if not memories:
            return ""
        lines = ["## Project Memory\n"]
        for memory in memories:
            lines.append(f"- [{memory.category}] **{memory.key}**: {memory.value}")
        lines.append("")
        return "\n".join(lines)
