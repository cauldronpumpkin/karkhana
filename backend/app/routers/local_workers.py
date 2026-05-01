from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.local_workers import DEFAULT_CAPABILITIES, LocalWorkerService

router = APIRouter(prefix="/api/local-workers", tags=["local-workers"])

_service: LocalWorkerService | None = None


def get_service() -> LocalWorkerService:
    global _service
    if _service is None:
        _service = LocalWorkerService()
    return _service


class WorkerRegisterRequest(BaseModel):
    display_name: str | None = None
    machine_name: str = Field(..., min_length=1)
    platform: str = Field(..., min_length=1)
    engine: str = "opencode"
    capabilities: list[str] = Field(default_factory=lambda: DEFAULT_CAPABILITIES.copy())
    config: dict = Field(default_factory=dict)
    tenant_id: str | None = None


class DenyRequest(BaseModel):
    reason: str = ""


class WorkerEventRequest(BaseModel):
    type: str = Field(..., min_length=1)
    payload: dict = Field(default_factory=dict)


@router.post("/register", status_code=201)
async def register_worker(body: WorkerRegisterRequest):
    return await get_service().register_request(body.model_dump())


@router.get("/registrations/{request_id}")
async def get_registration(request_id: str, pairing_token: str = ""):
    try:
        return await get_service().get_registration(request_id, pairing_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("")
async def list_workers():
    return await get_service().dashboard()


@router.get("/requests")
async def list_requests():
    return await get_service().list_requests()


@router.post("/requests/{request_id}/approve")
async def approve_request(request_id: str):
    try:
        return await get_service().approve_request(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/requests/{request_id}/deny")
async def deny_request(request_id: str, body: DenyRequest | None = None):
    try:
        return await get_service().deny_request(request_id, body.reason if body else "")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{worker_id}/revoke")
async def revoke_worker(worker_id: str):
    try:
        return await get_service().revoke_worker(worker_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{worker_id}/rotate-credentials")
async def rotate_credentials(worker_id: str):
    try:
        return await get_service().rotate_credentials(worker_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{worker_id}/events")
async def post_worker_event(worker_id: str, body: WorkerEventRequest, authorization: str | None = Header(default=None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    try:
        await get_service().verify_worker_token(worker_id, token)
        return await get_service().process_worker_event(worker_id, body.type, body.payload)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
