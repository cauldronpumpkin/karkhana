from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.project_twin import ProjectTwinService, to_jsonable

router = APIRouter(tags=["project-twin"])

_service: ProjectTwinService | None = None


def get_service() -> ProjectTwinService:
    global _service
    if _service is None:
        _service = ProjectTwinService()
    return _service


class GitHubImportRequest(BaseModel):
    installation_id: str = Field(..., min_length=1)
    owner: str | None = None
    repo: str | None = None
    repo_full_name: str | None = None
    repo_url: str | None = None
    clone_url: str | None = None
    default_branch: str = "main"
    title: str | None = None
    description: str | None = None
    deploy_url: str | None = None
    current_status: str | None = None
    desired_outcome: str | None = None


@router.post("/api/ideas/import/github", status_code=201)
async def import_github_project(body: GitHubImportRequest):
    try:
        return await get_service().import_github_project(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/ideas/{idea_id}/project")
async def get_project_twin(idea_id: str):
    try:
        return await get_service().get_project_status(idea_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/ideas/{idea_id}/project/reindex")
async def reindex_project_twin(idea_id: str):
    try:
        job = await get_service().enqueue_reindex(idea_id)
        return {"job": to_jsonable(job)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/ideas/{idea_id}/jobs")
async def list_idea_jobs(idea_id: str):
    return {"jobs": await get_service().list_jobs(idea_id)}


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    for job in await get_service().list_jobs():
        if job["id"] == job_id:
            return {"job": job}
    raise HTTPException(status_code=404, detail="Job not found")
