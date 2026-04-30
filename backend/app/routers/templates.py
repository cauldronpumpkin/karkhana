from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.template_pack import TemplatePackService


router = APIRouter(tags=["templates"])

_service: TemplatePackService | None = None


def get_service() -> TemplatePackService:
    global _service
    if _service is None:
        _service = TemplatePackService()
    return _service


class ValidateTemplateRequest(BaseModel):
    changed_files: list[str] = Field(default_factory=list)
    mode: str = Field(default="normal")
    verification_commands: list[str] = Field(default_factory=list)
    graphify_updated: bool | None = None
    completed: bool = False
    target_path: str | None = None


@router.get("/api/templates")
async def list_templates():
    return {"template_packs": await get_service().list_template_packs()}


@router.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    pack = await get_service().get_template_pack(template_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Template pack not found")
    return {"template_pack": pack}


@router.get("/api/templates/{template_id}/manifest")
async def get_template_manifest(template_id: str):
    manifest = await get_service().get_template_manifest(template_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Template manifest not found")
    return {"manifest": manifest}


@router.get("/api/templates/{template_id}/context-cards")
async def get_template_context_cards(template_id: str):
    payload = await get_service().get_template_context_cards(template_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Template context cards not found")
    return payload


@router.post("/api/templates/{template_id}/validate")
async def validate_template(template_id: str, body: ValidateTemplateRequest | None = None):
    try:
        payload = body or ValidateTemplateRequest()
        result = await get_service().validate_template(
            template_id,
            changed_files=payload.changed_files,
            mode=payload.mode,
            verification_commands=payload.verification_commands,
            graphify_updated=payload.graphify_updated,
            completed=payload.completed,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
