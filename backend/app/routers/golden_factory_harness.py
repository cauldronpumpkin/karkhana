from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.services.golden_factory_harness import GoldenFactoryHarnessService


router = APIRouter(tags=["golden-factory-harness"])

_service: GoldenFactoryHarnessService | None = None


def get_service() -> GoldenFactoryHarnessService:
    global _service
    if _service is None:
        _service = GoldenFactoryHarnessService()
    return _service


@router.get("/api/templates/{template_id}/golden-factory-harness")
async def get_golden_factory_harness(template_id: str, include_deferred: bool = False):
    harness = await get_service().get_harness(template_id, include_deferred=include_deferred)
    if not harness:
        raise HTTPException(status_code=404, detail="Golden factory harness not found")
    return {"golden_factory_harness": harness}

