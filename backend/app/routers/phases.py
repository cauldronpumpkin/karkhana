from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.phase_engine import PhaseEngine

router = APIRouter(prefix="/api/ideas", tags=["phases"])

_engine: PhaseEngine | None = None


def get_engine() -> PhaseEngine:
    global _engine
    if _engine is None:
        _engine = PhaseEngine()
    return _engine


class RejectRequest(BaseModel):
    reason: str


@router.get("/{idea_id}/phase")
async def get_current_phase(idea_id: str):
    try:
        engine = get_engine()
        phase = await engine.get_current_phase(idea_id)
        return {"idea_id": idea_id, "current_phase": phase}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{idea_id}/phase/suggest")
async def suggest_advancement(idea_id: str):
    try:
        engine = get_engine()
        result = await engine.suggest_advancement(idea_id)
        return {"idea_id": idea_id, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{idea_id}/phase/approve")
async def approve_advancement(idea_id: str):
    try:
        engine = get_engine()
        new_phase = await engine.approve_advancement(idea_id)
        return {"idea_id": idea_id, "new_phase": new_phase}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{idea_id}/phase/reject")
async def reject_advancement(idea_id: str, body: RejectRequest):
    try:
        engine = get_engine()
        await engine.reject_advancement(idea_id, body.reason)
        return {"idea_id": idea_id, "status": "rejected", "reason": body.reason}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
