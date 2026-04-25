from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.repository import Idea, Score, get_repository

router = APIRouter()


class IdeaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)


class IdeaUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)


class ScoreResponse(BaseModel):
    dimension: str
    value: float
    rationale: str | None = None
    scored_at: datetime | None = None


class IdeaResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    current_phase: str
    composite_score: float
    created_at: datetime
    updated_at: datetime
    status: str
    source_type: str = "manual"


class IdeaDetailResponse(IdeaResponse):
    scores: list[ScoreResponse] | None = None


def _slug(title: str) -> str:
    return re.sub(r"[^\w-]", "", title.lower().replace(" ", "-")) or "idea"


def _idea_to_dict(idea: Idea, composite_score: float = 0.0) -> dict:
    return {
        "id": idea.id,
        "title": idea.title,
        "slug": idea.slug,
        "description": idea.description,
        "current_phase": idea.current_phase,
        "composite_score": composite_score,
        "created_at": idea.created_at,
        "updated_at": idea.updated_at,
        "status": idea.status,
        "source_type": idea.source_type,
    }


def _score_to_dict(score: Score) -> dict:
    return {
        "dimension": score.dimension,
        "value": score.value,
        "rationale": score.rationale,
        "scored_at": score.scored_at,
    }


async def _get_composite_score(idea_id: str) -> float:
    scores = await get_repository().list_scores(idea_id)
    if not scores:
        return 0.0
    return round(sum(s.value for s in scores) / len(scores), 2)


@router.post("/api/ideas", status_code=status.HTTP_201_CREATED)
async def create_idea(idea_data: IdeaCreate):
    repo = get_repository()
    idea = Idea(
        title=idea_data.title,
        slug=_slug(idea_data.title),
        description=idea_data.description,
    )
    await repo.create_idea(idea)
    return _idea_to_dict(idea)


@router.get("/api/ideas")
async def get_ideas():
    response = []
    for idea in await get_repository().list_active_ideas():
        response.append(_idea_to_dict(idea, await _get_composite_score(idea.id)))
    return response


@router.get("/api/ideas/{idea_id}")
async def get_idea(idea_id: str):
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea or idea.status != "active":
        raise HTTPException(status_code=404, detail="Idea not found")
    scores = await repo.list_scores(idea_id)
    return {
        **_idea_to_dict(idea, await _get_composite_score(idea_id)),
        "scores": [_score_to_dict(s) for s in scores] if scores else None,
    }


@router.patch("/api/ideas/{idea_id}")
async def update_idea(idea_id: str, idea_data: IdeaUpdate):
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea or idea.status != "active":
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea_data.title:
        idea.title = idea_data.title
        idea.slug = _slug(idea_data.title)
    if idea_data.description:
        idea.description = idea_data.description
    await repo.save_idea(idea)
    return _idea_to_dict(idea, await _get_composite_score(idea_id))


@router.delete("/api/ideas/{idea_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_idea(idea_id: str):
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea or idea.status != "active":
        raise HTTPException(status_code=404, detail="Idea not found")
    idea.status = "archived"
    await repo.save_idea(idea)
