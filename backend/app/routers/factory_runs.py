from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.autonomy import (
    AUTONOMY_AUTONOMOUS_DEVELOPMENT,
    validate_autonomy_level,
)
from backend.app.services.factory_run import FactoryRunService
from backend.app.services.policy_engine import PolicyBlockedError

router = APIRouter(tags=["factory-runs"])

_service: FactoryRunService | None = None


def get_service() -> FactoryRunService:
    global _service
    if _service is None:
        _service = FactoryRunService()
    return _service


class CreateFactoryRunRequest(BaseModel):
    template_id: str = Field(..., min_length=1)
    autonomy_level: str = Field(default=AUTONOMY_AUTONOMOUS_DEVELOPMENT)
    config: dict = Field(default_factory=dict)


@router.post("/api/projects/{project_id}/factory-runs", status_code=201)
async def create_factory_run(project_id: str, body: CreateFactoryRunRequest):
    try:
        validate_autonomy_level(body.autonomy_level)
        return await get_service().create_factory_run(
            project_id=project_id,
            template_id=body.template_id,
            autonomy_level=body.autonomy_level,
            config=body.config,
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
