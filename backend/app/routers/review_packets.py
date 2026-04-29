from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.review_packet import InvalidTransitionError, ReviewPacketService
from backend.app.services.policy_engine import PolicyBlockedError

router = APIRouter(tags=["review-packets"])

_service: ReviewPacketService | None = None


def get_service() -> ReviewPacketService:
    global _service
    if _service is None:
        _service = ReviewPacketService()
    return _service


class InterventionRequest(BaseModel):
    action: str = Field(..., min_length=1)
    rationale: str | None = None


class StartWaitWindowRequest(BaseModel):
    expires_at: str | None = None


class RecordExpiryRequest(BaseModel):
    pass


@router.post("/api/factory-runs/{factory_run_id}/review-packet", status_code=201)
async def create_review_packet(factory_run_id: str):
    try:
        return await get_service().create_review_packet(factory_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/factory-runs/{factory_run_id}/review-packet")
async def get_review_packet(factory_run_id: str):
    try:
        return await get_service().get_review_packet(factory_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/review-packets")
async def list_review_packets(filter: str | None = None):
    return await get_service().list_review_packets(filter_group=filter)


@router.post("/api/factory-runs/{factory_run_id}/review-packet/intervene")
async def submit_intervention(factory_run_id: str, body: InterventionRequest):
    try:
        return await get_service().submit_intervention(
            factory_run_id,
            body.action,
            rationale=body.rationale,
        )
    except PolicyBlockedError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        status_code = 404 if "not found" in msg else 400
        raise HTTPException(status_code=status_code, detail=msg) from exc


@router.post("/api/factory-runs/{factory_run_id}/review-packet/start-wait-window")
async def start_wait_window(factory_run_id: str, body: StartWaitWindowRequest | None = None):
    try:
        expires_at = body.expires_at if body else None
        return await get_service().start_wait_window(factory_run_id, expires_at=expires_at)
    except (InvalidTransitionError, ValueError) as exc:
        msg = str(exc)
        status_code = 404 if "not found" in msg else 409
        raise HTTPException(status_code=status_code, detail=msg) from exc


@router.post("/api/factory-runs/{factory_run_id}/review-packet/record-expiry")
async def record_expiry(factory_run_id: str):
    try:
        return await get_service().record_expiry_transition(factory_run_id)
    except (InvalidTransitionError, ValueError) as exc:
        msg = str(exc)
        status_code = 404 if "not found" in msg else 409
        raise HTTPException(status_code=status_code, detail=msg) from exc
