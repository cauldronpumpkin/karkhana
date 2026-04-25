from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.scoring import ScoringService

router = APIRouter(prefix="/api/ideas", tags=["scoring"])

_service: ScoringService | None = None


def get_service() -> ScoringService:
    global _service
    if _service is None:
        _service = ScoringService()
    return _service


class ScoreOverrideRequest(BaseModel):
    value: float
    rationale: str


class CompareRequest(BaseModel):
    idea_ids: list[str]


@router.post("/{idea_id}/score")
async def score_idea(idea_id: str):
    """AI scores idea on all 7 dimensions."""
    try:
        service = get_service()
        scores = await service.score_idea(idea_id)
        return {"idea_id": idea_id, "scores": scores}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{idea_id}/scores")
async def get_scores(idea_id: str):
    """Get all scores for an idea."""
    try:
        service = get_service()
        scores = await service.get_scores(idea_id)
        return {"idea_id": idea_id, "scores": scores}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{idea_id}/scores/composite")
async def get_composite_score(idea_id: str):
    """Get composite (weighted average) score."""
    try:
        service = get_service()
        composite = await service.get_composite_score(idea_id)
        return {"idea_id": idea_id, "composite_score": composite}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{idea_id}/scores/{dimension}")
async def rescore_dimension(idea_id: str, dimension: str, body: ScoreOverrideRequest):
    """Manual override for a single dimension score."""
    try:
        service = get_service()
        result = await service.rescore_dimension(
            idea_id=idea_id,
            dimension=dimension,
            value=body.value,
            rationale=body.rationale,
        )
        return {"idea_id": idea_id, "dimension": dimension, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/compare")
async def compare_ideas(body: CompareRequest):
    """Compare multiple ideas side-by-side."""
    try:
        service = get_service()
        comparison = await service.compare_ideas(body.idea_ids)
        return {"comparison": comparison}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
