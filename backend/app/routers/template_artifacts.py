from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.agents_md_artifact import AgentsMdArtifactService

router = APIRouter(tags=["template-artifacts"])

_service: AgentsMdArtifactService | None = None


def get_service() -> AgentsMdArtifactService:
    global _service
    if _service is None:
        _service = AgentsMdArtifactService()
    return _service


class ImportAgentsMdRequest(BaseModel):
    version: str = Field(default="1.0.0")
    compatibility: dict = Field(default_factory=dict)


@router.post("/api/templates/{template_id}/agents-md/import")
async def import_agents_md(template_id: str, body: ImportAgentsMdRequest):
    try:
        artifact = await get_service().import_from_disk(
            template_id=template_id,
            version=body.version,
            compatibility=body.compatibility or None,
        )
        return {
            "artifact": {
                "id": artifact.id,
                "template_id": artifact.template_id,
                "artifact_key": artifact.artifact_key,
                "version": artifact.version,
                "uri": artifact.uri,
                "content_type": artifact.content_type,
                "compatibility": artifact.compatibility,
                "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/templates/{template_id}/agents-md")
async def get_agents_md(template_id: str, version: str | None = None):
    artifact = await get_service().get_artifact(template_id, version=version)
    if not artifact:
        raise HTTPException(status_code=404, detail="AGENTS.md artifact not found")
    return {
        "artifact": {
            "id": artifact.id,
            "template_id": artifact.template_id,
            "artifact_key": artifact.artifact_key,
            "version": artifact.version,
            "uri": artifact.uri,
            "content_type": artifact.content_type,
            "content": artifact.content,
            "compatibility": artifact.compatibility,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        }
    }


@router.get("/api/templates/{template_id}/agents-md/versions")
async def list_agents_md_versions(template_id: str):
    versions = await get_service().list_versions(template_id)
    return {"versions": versions}
