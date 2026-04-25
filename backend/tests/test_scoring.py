"""Tests for the Scoring service."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.services.scoring import SCORING_DIMENSIONS, ScoringService


@pytest.mark.asyncio
async def test_score_idea_returns_all_dimensions(sample_idea):
    """Happy path: score_idea returns scores for all 7 dimensions."""
    mock_response = _build_scoring_json()
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync(mock_response)

        scores = await service.score_idea(sample_idea.id)
        assert isinstance(scores, dict)
        for dim in SCORING_DIMENSIONS:
            assert dim in scores
            assert "value" in scores[dim]
            assert "rationale" in scores[dim]


@pytest.mark.asyncio
async def test_score_idea_not_found():
    """Edge case: score_idea raises ValueError for nonexistent idea."""
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync("{}")

        with pytest.raises(ValueError, match="Idea not found"):
            await service.score_idea("nonexistent-id")


@pytest.mark.asyncio
async def test_rescore_dimension(db_session, sample_idea):
    """Happy path: rescore_dimension updates a single dimension."""
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync("{}")

        result = await service.rescore_dimension(
            idea_id=sample_idea.id,
            dimension="tam",
            value=8.5,
            rationale="Large market opportunity",
        )
        assert result["value"] == 8.5
        assert result["rationale"] == "Large market opportunity"


@pytest.mark.asyncio
async def test_rescore_dimension_invalid_dimension(db_session, sample_idea):
    """Edge case: rescore_dimension raises ValueError for invalid dimension."""
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync("{}")

        with pytest.raises(ValueError, match="Invalid dimension"):
            await service.rescore_dimension(
                idea_id=sample_idea.id,
                dimension="invalid_dim",
                value=5.0,
                rationale="test",
            )


@pytest.mark.asyncio
async def test_rescore_dimension_clamps_value(db_session, sample_idea):
    """Edge case: rescore_dimension clamps value to 0-10 range."""
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync("{}")

        result = await service.rescore_dimension(
            idea_id=sample_idea.id,
            dimension="tam",
            value=15.0,
            rationale="test",
        )
        assert result["value"] == 10.0

        result = await service.rescore_dimension(
            idea_id=sample_idea.id,
            dimension="competition",
            value=-5.0,
            rationale="test",
        )
        assert result["value"] == 0.0


@pytest.mark.asyncio
async def test_get_scores(db_session, sample_idea):
    """Happy path: get_scores returns list of scores."""
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync("{}")

        await service.rescore_dimension(sample_idea.id, "tam", 7.0, "Good TAM")
        scores = await service.get_scores(sample_idea.id)
        assert isinstance(scores, list)
        assert len(scores) == 1
        assert scores[0]["dimension"] == "tam"
        assert scores[0]["value"] == 7.0


@pytest.mark.asyncio
async def test_get_composite_score(db_session, sample_idea):
    """Happy path: get_composite_score returns average of all scores."""
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync("{}")

        await service.rescore_dimension(sample_idea.id, "tam", 8.0, "")
        await service.rescore_dimension(sample_idea.id, "competition", 6.0, "")
        composite = await service.get_composite_score(sample_idea.id)
        assert composite == 7.0


@pytest.mark.asyncio
async def test_get_composite_score_no_scores(db_session, sample_idea):
    """Edge case: get_composite_score returns 0.0 when no scores exist."""
    with patch.object(ScoringService, "__init__", lambda self: None):
        service = ScoringService()
        service.llm = _mock_llm_sync("{}")

        composite = await service.get_composite_score(sample_idea.id)
        assert composite == 0.0


def _build_scoring_json() -> str:
    """Build a valid JSON scoring response."""
    import json
    data = {}
    for dim in SCORING_DIMENSIONS:
        data[dim] = {"value": 7.0, "rationale": f"Mock rationale for {dim}"}
    return json.dumps(data)


def _mock_llm_sync(response: str):
    """Create a mock LLM service with a canned sync response."""
    from backend.tests.conftest import MockLLMService
    return MockLLMService(responses={"": response})
