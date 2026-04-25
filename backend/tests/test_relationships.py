"""Tests for the Relationships service."""
from __future__ import annotations

import pytest

from backend.app.services.relationships import RelationshipService


@pytest.mark.asyncio
async def test_create_relationship(db_session, sample_idea, sample_idea_two):
    """Happy path: create_relationship links two ideas."""
    service = RelationshipService()
    result = await service.create_relationship(
        source_id=sample_idea.id,
        target_id=sample_idea_two.id,
        relation_type="reference",
        description="Related idea",
    )
    assert result["source_idea_id"] == sample_idea.id
    assert result["target_idea_id"] == sample_idea_two.id
    assert result["relation_type"] == "reference"


@pytest.mark.asyncio
async def test_create_relationship_source_not_found(db_session, sample_idea_two):
    """Edge case: create_relationship raises ValueError for nonexistent source."""
    service = RelationshipService()
    with pytest.raises(ValueError, match="Source idea.*not found"):
        await service.create_relationship(
            source_id="nonexistent-source",
            target_id=sample_idea_two.id,
            relation_type="reference",
        )


@pytest.mark.asyncio
async def test_create_relationship_target_not_found(db_session, sample_idea):
    """Edge case: create_relationship raises ValueError for nonexistent target."""
    service = RelationshipService()
    with pytest.raises(ValueError, match="Target idea.*not found"):
        await service.create_relationship(
            source_id=sample_idea.id,
            target_id="nonexistent-target",
            relation_type="reference",
        )


@pytest.mark.asyncio
async def test_get_relationships(db_session, sample_idea, sample_idea_two):
    """Happy path: get_relationships returns relationships for an idea."""
    service = RelationshipService()
    await service.create_relationship(
        source_id=sample_idea.id,
        target_id=sample_idea_two.id,
        relation_type="reference",
    )

    relationships = await service.get_relationships(sample_idea.id)
    assert isinstance(relationships, list)
    assert len(relationships) >= 1


@pytest.mark.asyncio
async def test_merge_ideas(db_session, sample_idea, sample_idea_two):
    """Happy path: merge_ideas creates a new merged idea and archives originals."""
    service = RelationshipService()
    result = await service.merge_ideas(
        source_id=sample_idea.id,
        target_id=sample_idea_two.id,
        merged_title="Merged Idea",
        merged_description="Combined description",
    )
    assert result["title"] == "Merged Idea"
    assert result["slug"] == "merged-idea"
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_split_idea(db_session, sample_idea):
    """Happy path: split_idea creates two new ideas and archives original."""
    service = RelationshipService()
    result = await service.split_idea(
        idea_id=sample_idea.id,
        split_data={
            "idea_a": {"title": "Split A", "description": "First half"},
            "idea_b": {"title": "Split B", "description": "Second half"},
            "messages_a": [],
            "messages_b": [],
        },
    )
    assert "idea_a" in result
    assert "idea_b" in result
    assert result["idea_a"]["title"] == "Split A"
    assert result["idea_b"]["title"] == "Split B"


@pytest.mark.asyncio
async def test_split_idea_missing_title(db_session, sample_idea):
    """Edge case: split_idea raises ValueError when title is missing."""
    service = RelationshipService()
    with pytest.raises(ValueError, match="must have a title"):
        await service.split_idea(
            idea_id=sample_idea.id,
            split_data={
                "idea_a": {"title": "", "description": ""},
                "idea_b": {"title": "Split B", "description": ""},
                "messages_a": [],
                "messages_b": [],
            },
        )


@pytest.mark.asyncio
async def test_derive_idea(db_session, sample_idea):
    """Happy path: derive_idea creates a new derived idea."""
    service = RelationshipService()
    result = await service.derive_idea(
        source_id=sample_idea.id,
        new_title="Derived Idea",
        new_description="Derived from original",
    )
    assert result["title"] == "Derived Idea"
    assert result["slug"] == "derived-idea"
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_derive_idea_source_not_found():
    """Edge case: derive_idea raises ValueError for nonexistent source."""
    service = RelationshipService()
    with pytest.raises(ValueError, match="Source idea.*not found"):
        await service.derive_idea(
            source_id="nonexistent-id",
            new_title="Derived",
            new_description="test",
        )
