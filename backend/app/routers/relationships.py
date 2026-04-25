from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.relationships import RelationshipService

router = APIRouter(prefix="/api/ideas", tags=["relationships"])

_service: RelationshipService | None = None


def get_service() -> RelationshipService:
    global _service
    if _service is None:
        _service = RelationshipService()
    return _service


class CreateRelationshipRequest(BaseModel):
    target_id: str = Field(..., description="Target idea ID")
    relation_type: str = Field(..., description="Type: merge, split, derive, reference")
    description: str | None = Field(None)


class MergeRequest(BaseModel):
    target_id: str = Field(..., description="Idea to merge with")
    merged_title: str = Field(..., description="Title for merged idea")
    merged_description: str = Field(..., description="Description for merged idea")


class SplitIdeaData(BaseModel):
    title: str
    description: str = ""


class SplitRequest(BaseModel):
    idea_a: SplitIdeaData
    idea_b: SplitIdeaData
    messages_a: list[str] = Field(default_factory=list, description="Message IDs for idea A")
    messages_b: list[str] = Field(default_factory=list, description="Message IDs for idea B")


class DeriveRequest(BaseModel):
    new_title: str = Field(..., description="Title for derived idea")
    new_description: str = Field(..., description="Description for derived idea")


@router.post("/{idea_id}/relationships")
async def create_relationship(idea_id: str, body: CreateRelationshipRequest):
    """Create a relationship between two ideas."""
    try:
        service = get_service()
        result = await service.create_relationship(
            source_id=idea_id,
            target_id=body.target_id,
            relation_type=body.relation_type,
            description=body.description,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{idea_id}/relationships")
async def get_relationships(idea_id: str):
    """Get all relationships for an idea."""
    try:
        service = get_service()
        relationships = await service.get_relationships(idea_id)
        return {"idea_id": idea_id, "relationships": relationships}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/merge")
async def merge_ideas(idea_id: str, body: MergeRequest):
    """Merge this idea with another."""
    try:
        service = get_service()
        result = await service.merge_ideas(
            source_id=idea_id,
            target_id=body.target_id,
            merged_title=body.merged_title,
            merged_description=body.merged_description,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/split")
async def split_idea(idea_id: str, body: SplitRequest):
    """Split an idea into two new ideas."""
    try:
        service = get_service()
        split_data = {
            "idea_a": {"title": body.idea_a.title, "description": body.idea_a.description},
            "idea_b": {"title": body.idea_b.title, "description": body.idea_b.description},
            "messages_a": body.messages_a,
            "messages_b": body.messages_b,
        }
        result = await service.split_idea(idea_id=idea_id, split_data=split_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/derive")
async def derive_idea(idea_id: str, body: DeriveRequest):
    """Create a derivative idea."""
    try:
        service = get_service()
        result = await service.derive_idea(
            source_id=idea_id,
            new_title=body.new_title,
            new_description=body.new_description,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{idea_id}/suggest-relationships")
async def suggest_relationships(idea_id: str):
    """AI suggests related ideas."""
    try:
        service = get_service()
        suggestions = await service.detect_related_ideas(idea_id)
        return {"idea_id": idea_id, "suggestions": suggestions}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
