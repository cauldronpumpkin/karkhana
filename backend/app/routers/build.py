from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.build_handoff import BuildHandoffService

router = APIRouter(prefix="/api/ideas", tags=["build"])

_service: BuildHandoffService | None = None


def get_service() -> BuildHandoffService:
    global _service
    if _service is None:
        _service = BuildHandoffService()
    return _service


class StepCompleteRequest(BaseModel):
    step: str


@router.get("/{idea_id}/build/prompts")
async def get_build_prompts(idea_id: str):
    """Get all build prompts (prometheus prompt + step prompts)."""
    try:
        service = get_service()
        prometheus_prompt = await service.generate_prometheus_prompt(idea_id)
        step_prompts = await service.generate_step_prompts(idea_id)
        return {
            "idea_id": idea_id,
            "prometheus_prompt": prometheus_prompt,
            "step_prompts": step_prompts,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{idea_id}/build/current-step")
async def get_current_step(idea_id: str):
    """Get current build step, completed steps, and remaining steps."""
    try:
        service = get_service()
        state = await service.get_current_build_state(idea_id)
        return state
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{idea_id}/build/next-actions")
async def get_next_actions(idea_id: str):
    """Get deterministic next actions for the current idea."""
    try:
        service = get_service()
        return await service.get_next_actions(idea_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/build/step-complete")
async def mark_step_complete(idea_id: str, body: StepCompleteRequest):
    """Mark a build step as complete and get the next step prompt."""
    try:
        service = get_service()
        result = await service.mark_step_complete(idea_id, body.step)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/build/regenerate")
async def regenerate_prompts(idea_id: str):
    """Regenerate all build prompts."""
    try:
        service = get_service()
        prometheus_prompt = await service.generate_prometheus_prompt(idea_id)
        step_prompts = await service.generate_step_prompts(idea_id)
        return {
            "idea_id": idea_id,
            "prometheus_prompt": prometheus_prompt,
            "step_prompts": step_prompts,
            "status": "regenerated",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
