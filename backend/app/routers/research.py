from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.app.services.research import ResearchService

router = APIRouter(prefix="/api/ideas", tags=["research"])

_service: ResearchService | None = None


def get_service() -> ResearchService:
    global _service
    if _service is None:
        _service = ResearchService()
    return _service


class GenerateResponse(BaseModel):
    idea_id: str
    prompts: list[dict]


class TaskResponse(BaseModel):
    id: str
    idea_id: str
    prompt_text: str
    status: str
    result_file_path: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class TasksListResponse(BaseModel):
    idea_id: str
    pending: list[TaskResponse]
    completed: list[TaskResponse]


class UploadResponse(BaseModel):
    idea_id: str
    task_id: str
    result_path: str


class IntegrateResponse(BaseModel):
    idea_id: str
    integration: dict


@router.post("/{idea_id}/research/generate")
async def generate_research_prompts(idea_id: str):
    """AI generates research prompts for knowledge gaps."""
    try:
        service = get_service()
        prompts = await service.generate_research_prompts(idea_id)
        return {"idea_id": idea_id, "prompts": prompts}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{idea_id}/research/tasks")
async def list_research_tasks(idea_id: str):
    """List all research tasks for an idea."""
    try:
        service = get_service()
        pending = await service.get_pending_tasks(idea_id)
        completed = await service.get_completed_tasks(idea_id)
        return {
            "idea_id": idea_id,
            "pending": pending,
            "completed": completed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/research/{task_id}/upload")
async def upload_research_result(idea_id: str, task_id: str, file: UploadFile = File(...)):
    """Upload research result file (multipart/form-data)."""
    # Validate file extension
    filename = file.filename or ""
    allowed_extensions = {".md", ".txt", ".markdown"}
    file_ext = ""
    if "." in filename:
        file_ext = "." + filename.rsplit(".", 1)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '{file_ext}'. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # Validate file size (< 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")

    try:
        service = get_service()
        result_path = await service.upload_research_result(
            idea_id=idea_id,
            task_id=task_id,
            content=content.decode("utf-8"),
        )
        return {"idea_id": idea_id, "task_id": task_id, "result_path": result_path}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/research/{task_id}/integrate")
async def integrate_research(idea_id: str, task_id: str):
    """AI integrates research result and produces summary + insights."""
    try:
        service = get_service()
        result = await service.integrate_research(idea_id, task_id)
        return {"idea_id": idea_id, "integration": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
