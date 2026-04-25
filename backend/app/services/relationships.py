from __future__ import annotations

import json
import re
import uuid

from backend.app.repository import Idea, IdeaRelationship, Message, Score, get_repository
from backend.app.services.llm import LLMService


def _slug(title: str) -> str:
    return re.sub(r"[^\w-]", "", title.lower().replace(" ", "-")) or "idea"


def _idea_dict(idea: Idea) -> dict:
    return {
        "id": idea.id,
        "title": idea.title,
        "slug": idea.slug,
        "description": idea.description,
        "current_phase": idea.current_phase,
        "status": idea.status,
        "created_at": idea.created_at.isoformat(),
        "updated_at": idea.updated_at.isoformat(),
    }


class RelationshipService:
    def __init__(self) -> None:
        self._llm: LLMService | None = None

    def _get_llm(self) -> LLMService:
        if self._llm is None:
            self._llm = LLMService()
        return self._llm

    async def create_relationship(self, source_id: str, target_id: str, relation_type: str, description: str | None = None) -> dict:
        repo = get_repository()
        if not await repo.get_idea(source_id):
            raise ValueError(f"Source idea {source_id} not found")
        if not await repo.get_idea(target_id):
            raise ValueError(f"Target idea {target_id} not found")
        relationship = await repo.add_relationship(IdeaRelationship(source_idea_id=source_id, target_idea_id=target_id, relation_type=relation_type, description=description))
        return self._relationship_dict(relationship)

    async def get_relationships(self, idea_id: str) -> list[dict]:
        repo = get_repository()
        if not await repo.get_idea(idea_id):
            raise ValueError(f"Idea {idea_id} not found")
        return [self._relationship_dict(r) for r in await repo.list_relationships(idea_id)]

    async def merge_ideas(self, source_id: str, target_id: str, merged_title: str, merged_description: str) -> dict:
        repo = get_repository()
        source = await repo.get_idea(source_id)
        target = await repo.get_idea(target_id)
        if not source:
            raise ValueError(f"Source idea {source_id} not found")
        if not target:
            raise ValueError(f"Target idea {target_id} not found")
        merged = await repo.create_idea(Idea(id=str(uuid.uuid4()), title=merged_title, slug=_slug(merged_title), description=merged_description))
        for original_id in [source_id, target_id]:
            for msg in await repo.list_messages(original_id):
                await repo.add_message(Message(idea_id=merged.id, role=msg.role, content=msg.content, timestamp=msg.timestamp, metadata_=msg.metadata_))
            for score in await repo.list_scores(original_id):
                await repo.put_score(Score(idea_id=merged.id, dimension=score.dimension, value=score.value, rationale=score.rationale, scored_at=score.scored_at))
            await repo.add_relationship(IdeaRelationship(source_idea_id=original_id, target_idea_id=merged.id, relation_type="merge", description=f"Merged into '{merged_title}'"))
        source.status = "archived"
        target.status = "archived"
        await repo.save_idea(source)
        await repo.save_idea(target)
        return _idea_dict(merged)

    async def split_idea(self, idea_id: str, split_data: dict) -> dict:
        repo = get_repository()
        original = await repo.get_idea(idea_id)
        if not original:
            raise ValueError(f"Idea {idea_id} not found")
        idea_a_data = split_data.get("idea_a", {})
        idea_b_data = split_data.get("idea_b", {})
        if not idea_a_data.get("title") or not idea_b_data.get("title"):
            raise ValueError("Both idea_a and idea_b must have a title")
        idea_a = await repo.create_idea(Idea(title=idea_a_data["title"], slug=_slug(idea_a_data["title"]), description=idea_a_data.get("description", "")))
        idea_b = await repo.create_idea(Idea(title=idea_b_data["title"], slug=_slug(idea_b_data["title"]), description=idea_b_data.get("description", "")))
        message_groups = [(idea_a.id, set(split_data.get("messages_a", []))), (idea_b.id, set(split_data.get("messages_b", [])))]
        original_messages = await repo.list_messages(idea_id)
        for new_id, selected_ids in message_groups:
            for msg in original_messages:
                if msg.id in selected_ids:
                    await repo.add_message(Message(idea_id=new_id, role=msg.role, content=msg.content, timestamp=msg.timestamp, metadata_=msg.metadata_))
            await repo.add_relationship(IdeaRelationship(source_idea_id=idea_id, target_idea_id=new_id, relation_type="split", description=f"Split from '{original.title}'"))
        original.status = "archived"
        await repo.save_idea(original)
        return {"idea_a": _idea_dict(idea_a), "idea_b": _idea_dict(idea_b)}

    async def derive_idea(self, source_id: str, new_title: str, new_description: str) -> dict:
        repo = get_repository()
        source = await repo.get_idea(source_id)
        if not source:
            raise ValueError(f"Source idea {source_id} not found")
        new_idea = await repo.create_idea(Idea(title=new_title, slug=_slug(new_title), description=new_description))
        await repo.add_relationship(IdeaRelationship(source_idea_id=source_id, target_idea_id=new_idea.id, relation_type="derive", description=f"Derived from '{source.title}'"))
        return _idea_dict(new_idea)

    async def detect_related_ideas(self, idea_id: str) -> list[dict]:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        if not idea:
            raise ValueError(f"Idea {idea_id} not found")
        other_ideas = [other for other in await repo.list_active_ideas() if other.id != idea_id]
        if not other_ideas:
            return []
        other_ideas_text = "\n".join(f"- ID: {other.id}, Title: {other.title}, Description: {other.description}" for other in other_ideas)
        prompt = (
            f"Given the following idea:\nTitle: {idea.title}\nDescription: {idea.description}\n\n"
            f"Which of these other ideas might be related? Return a JSON array of objects with 'idea_id', "
            f"'relation_type' (one of: reference, derive), and 'reason'.\n\nOther ideas:\n{other_ideas_text}\n\n"
            f"Return ONLY valid JSON, no markdown formatting."
        )
        try:
            suggestions = json.loads((await self._get_llm().chat_completion_sync(messages=[{"role": "user", "content": prompt}])).strip())
            return suggestions if isinstance(suggestions, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _relationship_dict(rel: IdeaRelationship) -> dict:
        return {
            "id": rel.id,
            "source_idea_id": rel.source_idea_id,
            "target_idea_id": rel.target_idea_id,
            "relation_type": rel.relation_type,
            "description": rel.description,
            "created_at": rel.created_at.isoformat(),
        }
