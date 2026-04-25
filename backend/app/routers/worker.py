from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.services.project_twin import ProjectTwinService

router = APIRouter(prefix="/api/worker", tags=["worker"])

_service: ProjectTwinService | None = None


def get_service() -> ProjectTwinService:
    global _service
    if _service is None:
        _service = ProjectTwinService()
    return _service


def verify_worker(x_idearefinery_worker_token: str | None) -> None:
    if settings.worker_auth_token and x_idearefinery_worker_token != settings.worker_auth_token:
        raise HTTPException(status_code=401, detail="Invalid worker token")


class ClaimRequest(BaseModel):
    worker_id: str = Field(..., min_length=1)
    capabilities: list[str] | None = None


class JobUpdateRequest(BaseModel):
    worker_id: str = Field(..., min_length=1)
    claim_token: str = Field(..., min_length=1)
    logs: str = ""


class JobCompleteRequest(JobUpdateRequest):
    result: dict = Field(default_factory=dict)


class JobFailRequest(JobUpdateRequest):
    error: str = Field(..., min_length=1)
    retryable: bool = True


@router.post("/claim")
async def claim_job(body: ClaimRequest, x_idearefinery_worker_token: str | None = Header(default=None)):
    verify_worker(x_idearefinery_worker_token)
    claim = await get_service().claim_job(body.worker_id, body.capabilities)
    return {"claim": claim}


@router.post("/jobs/{job_id}/heartbeat")
async def heartbeat_job(job_id: str, body: JobUpdateRequest, x_idearefinery_worker_token: str | None = Header(default=None)):
    verify_worker(x_idearefinery_worker_token)
    try:
        return {"job": await get_service().heartbeat_job(job_id, body.claim_token, body.worker_id, body.logs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/complete")
async def complete_job(job_id: str, body: JobCompleteRequest, x_idearefinery_worker_token: str | None = Header(default=None)):
    verify_worker(x_idearefinery_worker_token)
    try:
        return {"job": await get_service().complete_job(job_id, body.claim_token, body.worker_id, body.result, body.logs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/fail")
async def fail_job(job_id: str, body: JobFailRequest, x_idearefinery_worker_token: str | None = Header(default=None)):
    verify_worker(x_idearefinery_worker_token)
    try:
        return {"job": await get_service().fail_job(job_id, body.claim_token, body.worker_id, body.error, body.retryable, body.logs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
