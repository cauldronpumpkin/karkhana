from __future__ import annotations

from fastapi import APIRouter

from backend.app.services.llm import LLMService

router = APIRouter(prefix="/api/ai", tags=["ai"])

llm_service = LLMService()


@router.get("/models")
async def list_ai_models():
    return {
        "active": llm_service.get_provider(),
        "providers": await llm_service.list_providers(discover=True),
    }
