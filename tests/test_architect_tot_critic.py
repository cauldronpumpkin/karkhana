"""Tests for architecture ToT candidate generation and critic selection."""

from __future__ import annotations

import asyncio

from src.graph import flow
from src.types.state import WorkingState


def test_architect_generates_candidates_and_critic_selects_winner(monkeypatch) -> None:
    async def fake_candidates(self, prd, count, parallel, thinking_modules_enabled):  # noqa: ANN001
        _ = (self, prd, count, parallel, thinking_modules_enabled)
        return [
            {"file_tree": {"src/": ["a.py"]}, "candidate_meta": {"candidate_id": 1}},
            {"file_tree": {"src/": ["b.py"]}, "candidate_meta": {"candidate_id": 2}},
            {"file_tree": {"src/": ["c.py"]}, "candidate_meta": {"candidate_id": 3}},
        ]

    async def fake_debate(self, prd, candidates, thinking_modules_enabled):  # noqa: ANN001
        _ = (self, prd, candidates, thinking_modules_enabled)
        return {"winner_index": 2, "winner_score": 91, "debate": []}

    monkeypatch.setattr(flow.ArchitectAgent, "generate_architecture_candidates", fake_candidates)
    monkeypatch.setattr(flow.CriticAgent, "debate_architecture_candidates", fake_debate)

    state = WorkingState(
        raw_idea="x",
        prd={"title": "t", "problem_statement": "p", "core_features": []},
        reasoning_config={
            "enabled": True,
            "profile": "balanced",
            "architect_tot_paths": 3,
            "architect_tot_parallel": True,
            "critic_enabled": True,
            "thinking_modules_enabled": True,
            "thinking_visibility": "logs",
            "tdd_enabled": True,
            "tdd_time_split_percent": 40,
            "tdd_max_iterations": 5,
            "tdd_fail_open": True,
        },
    )
    result = asyncio.run(flow.architect_agent_node(state))
    assert len(result["architecture_candidates"]) == 3
    assert result["critic_report"]["winner_index"] == 2
    assert result["tech_stack"]["candidate_meta"]["candidate_id"] == 3


def test_architect_critic_failure_falls_back_to_first_candidate(monkeypatch) -> None:
    async def fake_candidates(self, prd, count, parallel, thinking_modules_enabled):  # noqa: ANN001
        _ = (self, prd, count, parallel, thinking_modules_enabled)
        return [
            {"file_tree": {"src/": ["a.py"]}, "candidate_meta": {"candidate_id": 1}},
            {"file_tree": {"src/": ["b.py"]}, "candidate_meta": {"candidate_id": 2}},
        ]

    async def failing_debate(self, prd, candidates, thinking_modules_enabled):  # noqa: ANN001
        _ = (self, prd, candidates, thinking_modules_enabled)
        raise RuntimeError("critic failed")

    monkeypatch.setattr(flow.ArchitectAgent, "generate_architecture_candidates", fake_candidates)
    monkeypatch.setattr(flow.CriticAgent, "debate_architecture_candidates", failing_debate)

    state = WorkingState(
        raw_idea="x",
        prd={"title": "t", "problem_statement": "p", "core_features": []},
        reasoning_config={"enabled": True, "profile": "balanced"},
    )
    result = asyncio.run(flow.architect_agent_node(state))
    assert result["critic_report"]["winner_index"] == 0
    assert result["tech_stack"]["candidate_meta"]["candidate_id"] == 1
