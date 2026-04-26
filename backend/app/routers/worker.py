from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.services.local_workers import LocalWorkerService
from backend.app.services.project_twin import ProjectTwinService

router = APIRouter(prefix="/api/worker", tags=["worker"])

_service: ProjectTwinService | None = None


def get_service() -> ProjectTwinService:
    global _service
    if _service is None:
        _service = ProjectTwinService()
    return _service


async def verify_worker(worker_id: str, x_idearefinery_worker_token: str | None, authorization: str | None) -> None:
    if settings.worker_auth_token and x_idearefinery_worker_token == settings.worker_auth_token:
        return
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token:
        try:
            await LocalWorkerService().verify_worker_token(worker_id, token)
            return
        except (PermissionError, ValueError) as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    if settings.worker_auth_token:
        raise HTTPException(status_code=401, detail="Invalid worker token")


class InviteLinkRequest(BaseModel):
    worker_id: str | None = Field(default=None, min_length=1)
    api_base: str | None = Field(default=None)


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


@router.get("/invite-link")
async def get_invite_link(
    api_base: str | None = Query(default=None),
    worker_id: str | None = Query(default=None),
):
    """Generate an invite link for worker pairing."""
    if not settings.worker_auth_token:
        raise HTTPException(status_code=503, detail="Worker auth token not configured on server")

    import urllib.parse

    resolved_base = (api_base or "").rstrip("/") or None
    if not resolved_base:
        raise HTTPException(status_code=400, detail="api_base query parameter is required")

    resolved_worker_id = worker_id or "local-worker"

    params = urllib.parse.urlencode({
        "api_base": resolved_base,
        "token": settings.worker_auth_token,
        "w": resolved_worker_id,
    })
    invite_link = f"idearefinery://connect?{params}"

    return {
        "invite_link": invite_link,
        "worker_id": resolved_worker_id,
        "api_base": resolved_base,
    }


@router.post("/claim")
async def claim_job(body: ClaimRequest, x_idearefinery_worker_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    await verify_worker(body.worker_id, x_idearefinery_worker_token, authorization)
    claim = await get_service().claim_job(body.worker_id, body.capabilities)
    return {"claim": claim}


@router.post("/jobs/{job_id}/heartbeat")
async def heartbeat_job(job_id: str, body: JobUpdateRequest, x_idearefinery_worker_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    await verify_worker(body.worker_id, x_idearefinery_worker_token, authorization)
    try:
        return {"job": await get_service().heartbeat_job(job_id, body.claim_token, body.worker_id, body.logs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/complete")
async def complete_job(job_id: str, body: JobCompleteRequest, x_idearefinery_worker_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    await verify_worker(body.worker_id, x_idearefinery_worker_token, authorization)
    try:
        return {"job": await get_service().complete_job(job_id, body.claim_token, body.worker_id, body.result, body.logs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/fail")
async def fail_job(job_id: str, body: JobFailRequest, x_idearefinery_worker_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    await verify_worker(body.worker_id, x_idearefinery_worker_token, authorization)
    try:
        return {"job": await get_service().fail_job(job_id, body.claim_token, body.worker_id, body.error, body.retryable, body.logs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
