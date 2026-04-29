from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.autonomy import (
    AUTONOMY_AUTONOMOUS_DEVELOPMENT,
    validate_autonomy_level,
)
from backend.app.services.factory_run import FactoryRunService
from backend.app.services.review_packet import ReviewPacketService
from backend.app.services.policy_engine import PolicyBlockedError

router = APIRouter(tags=["factory-runs"])

_service: FactoryRunService | None = None
_review_service: ReviewPacketService | None = None


def get_service() -> FactoryRunService:
    global _service
    if _service is None:
        _service = FactoryRunService()
    return _service


def get_review_service() -> ReviewPacketService:
    global _review_service
    if _review_service is None:
        _review_service = ReviewPacketService()
    return _review_service


class CreateFactoryRunRequest(BaseModel):
    template_id: str = Field(..., min_length=1)
    autonomy_level: str = Field(default=AUTONOMY_AUTONOMOUS_DEVELOPMENT)
    config: dict = Field(default_factory=dict)
    intent: dict | None = None


class ResearchArtifactRequest(BaseModel):
    title: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    raw_content: str | None = None
    raw_content_uri: str | None = None
    raw_metadata: dict = Field(default_factory=dict)
    normalized: dict | None = None
    force: bool = False
    correlation_id: str | None = None
    actor: str = "system"


@router.post("/api/projects/{project_id}/factory-runs", status_code=201)
async def create_factory_run(project_id: str, body: CreateFactoryRunRequest):
    try:
        validate_autonomy_level(body.autonomy_level)
        return await get_service().create_factory_run(
            project_id=project_id,
            template_id=body.template_id,
            autonomy_level=body.autonomy_level,
            config=body.config,
            intent=body.intent,
        )
    except PolicyBlockedError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/projects/{project_id}/factory-runs")
async def list_factory_runs(project_id: str):
    try:
        return await get_service().list_factory_runs(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/factory-runs/{factory_run_id}")
async def get_factory_run(factory_run_id: str):
    try:
        return await get_service().get_factory_run(factory_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/factory-runs/{factory_run_id}/research-artifacts", status_code=201)
async def create_research_artifact(factory_run_id: str, body: ResearchArtifactRequest):
    try:
        return await get_service().create_research_artifact(
            factory_run_id,
            title=body.title,
            source=body.source,
            raw_content=body.raw_content,
            raw_content_uri=body.raw_content_uri,
            raw_metadata=body.raw_metadata,
            normalized=body.normalized,
            force=body.force,
            correlation_id=body.correlation_id,
            actor=body.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/factory-runs/{factory_run_id}/research-handoff", status_code=201)
async def create_research_handoff(factory_run_id: str):
    try:
        return await get_review_service().create_research_handoff(factory_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
