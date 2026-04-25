"""Tests for the Phase Engine service."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.services.phase_engine import PHASE_ORDER, PhaseEngine


@pytest.mark.asyncio
async def test_get_current_phase(sample_idea):
    """Happy path: get_current_phase returns the idea's current phase."""
    engine = PhaseEngine()
    phase = await engine.get_current_phase(sample_idea.id)
    assert phase == "capture"


@pytest.mark.asyncio
async def test_get_current_phase_not_found():
    """Edge case: get_current_phase raises ValueError for nonexistent idea."""
    engine = PhaseEngine()
    with pytest.raises(ValueError, match="Idea not found"):
        await engine.get_current_phase("nonexistent-id")


@pytest.mark.asyncio
async def test_suggest_advancement_returns_next_phase(sample_idea):
    """Happy path: suggest_advancement returns next phase in sequence."""
    mock_llm = _create_mock_llm('{"ready": true, "reasoning": "Good progress", "next_phase": "clarify"}')
    engine = PhaseEngine(llm_service=mock_llm)

    result = await engine.suggest_advancement(sample_idea.id)
    assert result["next_phase"] == "clarify"
    assert result["ready"] is True
    assert "reasoning" in result


@pytest.mark.asyncio
async def test_suggest_advancement_final_phase(db_session, sample_idea):
    """Edge case: suggest_advancement for build phase returns no advancement."""
    sample_idea.current_phase = "build"
    await db_session.commit()

    engine = PhaseEngine()
    result = await engine.suggest_advancement(sample_idea.id)
    assert result["ready"] is False
    assert "final phase" in result["reasoning"]


@pytest.mark.asyncio
async def test_approve_advancement_transitions_phase(db_session, sample_idea):
    """Happy path: approve_advancement transitions to next phase."""
    mock_llm = _create_mock_llm("# Mock phase report")
    engine = PhaseEngine(llm_service=mock_llm)

    new_phase = await engine.approve_advancement(sample_idea.id)
    assert new_phase == "clarify"

    # Verify idea was updated
    phase = await engine.get_current_phase(sample_idea.id)
    assert phase == "clarify"


@pytest.mark.asyncio
async def test_approve_advancement_final_phase(db_session, sample_idea):
    """Edge case: approve_advancement on final phase raises ValueError."""
    sample_idea.current_phase = "build"
    await db_session.commit()

    engine = PhaseEngine()
    with pytest.raises(ValueError, match="final phase"):
        await engine.approve_advancement(sample_idea.id)


@pytest.mark.asyncio
async def test_reject_advancement(db_session, sample_idea):
    """Happy path: reject_advancement keeps phase unchanged."""
    original_phase = sample_idea.current_phase
    engine = PhaseEngine()

    await engine.reject_advancement(sample_idea.id, "Need more details")

    phase = await engine.get_current_phase(sample_idea.id)
    assert phase == original_phase


@pytest.mark.asyncio
async def test_reject_advancement_not_found():
    """Edge case: reject_advancement for nonexistent idea raises ValueError."""
    engine = PhaseEngine()
    with pytest.raises(ValueError, match="Idea not found"):
        await engine.reject_advancement("nonexistent-id", "reason")


@pytest.mark.asyncio
async def test_get_phase_requirements():
    """Happy path: get_phase_requirements returns list for valid phase."""
    engine = PhaseEngine()
    requirements = engine.get_phase_requirements("capture")
    assert isinstance(requirements, list)
    assert len(requirements) > 0


@pytest.mark.asyncio
async def test_get_phase_requirements_unknown_phase():
    """Edge case: get_phase_requirements returns empty list for unknown phase."""
    engine = PhaseEngine()
    requirements = engine.get_phase_requirements("unknown_phase")
    assert requirements == []


def _create_mock_llm(response: str):
    """Create a mock LLM service with a canned response."""
    from backend.tests.conftest import MockLLMService
    return MockLLMService(responses={"": response})
