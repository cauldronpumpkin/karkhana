from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.repository import get_repository

router = APIRouter(prefix="/api/ideas", tags=["reports"])


class ReportResponse(BaseModel):
    id: str
    phase: str
    title: str
    content: str
    generated_at: datetime


class ReportsListResponse(BaseModel):
    reports: list[ReportResponse]


@router.get("/{idea_id}/reports")
async def get_idea_reports(idea_id: str):
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea or idea.status != "active":
        raise HTTPException(status_code=404, detail="Idea not found")
    return {
        "reports": [
            {"id": r.id, "phase": r.phase, "title": r.title, "content": r.content, "generated_at": r.generated_at}
            for r in await repo.list_reports(idea_id)
        ]
    }


@router.get("/{idea_id}/reports/{phase}")
async def get_idea_report(idea_id: str, phase: str):
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea or idea.status != "active":
        raise HTTPException(status_code=404, detail="Idea not found")
    report = await repo.get_report(idea_id, phase)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"id": report.id, "phase": report.phase, "title": report.title, "content": report.content, "generated_at": report.generated_at}
