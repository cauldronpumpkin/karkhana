from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.services.memory import MemoryService

router = APIRouter(tags=["memory"])

_service: MemoryService | None = None


def get_service() -> MemoryService:
    global _service
    if _service is None:
        _service = MemoryService()
    return _service


class MemoryCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)
    category: str = Field(..., pattern="^(stage|issue|bug|note|constraint|resource)$")


class MemoryResponse(BaseModel):
    id: str
    idea_id: str | None = None
    key: str
    value: str
    category: str
    created_at: str
    updated_at: str


def _memory_to_dict(memory) -> dict:
    return {
        "id": memory.id,
        "idea_id": memory.idea_id,
        "key": memory.key,
        "value": memory.value,
        "category": memory.category,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


@router.get("/api/memory", response_model=list[MemoryResponse])
async def get_all_global_memory():
    """Get all global memory entries (not tied to any idea)."""
    service = get_service()
    memories = await service.get_all_memory(idea_id=None)
    return [_memory_to_dict(m) for m in memories]


@router.get("/api/ideas/{idea_id}/memory", response_model=list[MemoryResponse])
async def get_idea_memory(idea_id: str):
    """Get all memory entries for a specific idea."""
    service = get_service()
    memories = await service.get_all_memory(idea_id=idea_id)
    return [_memory_to_dict(m) for m in memories]


@router.post(
    "/api/ideas/{idea_id}/memory",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_memory(idea_id: str, body: MemoryCreate):
    """Create or update a memory entry for an idea."""
    service = get_service()
    try:
        memory = await service.set_memory(
            key=body.key,
            value=body.value,
            category=body.category,
            idea_id=idea_id,
        )
        return _memory_to_dict(memory)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/api/ideas/{idea_id}/memory/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(idea_id: str, key: str):
    """Delete a memory entry for an idea."""
    service = get_service()
    deleted = await service.delete_memory(key=key, idea_id=idea_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory '{key}' not found for idea {idea_id}")
