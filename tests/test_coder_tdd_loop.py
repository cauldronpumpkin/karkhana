"""Tests for TDD reflection loop behavior in coder stage."""

from __future__ import annotations

import asyncio

from src.graph import flow
from src.types.state import WorkingState


class _FakeAdapter:
    def available(self) -> bool:
        return True

    def generate_test_command(self, *, file_path: str, test_file_path: str) -> list[str]:
        _ = (file_path, test_file_path)
        return ["echo", "test"]

    def generate_syntax_command(self, *, file_path: str) -> list[str]:
        _ = file_path
        return ["echo", "syntax"]


def test_tdd_loop_repairs_after_failure(monkeypatch) -> None:
    class FakeCoder:
        def set_runtime_context(self, **kwargs):  # noqa: ANN003
            _ = kwargs

        def generate_coordination_requests(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            return []

        def test_file_for(self, file_path: str) -> str:
            return "tests/test_main.py"

        async def write_tests(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            return {"code": "def test_ok():\n    assert True\n", "thinking": ""}

        async def write_impl_from_tests(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            return {"code": "def f():\n    return 1\n", "thinking": ""}

        async def repair_from_test_failure(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            return {"code": "def f():\n    return 2\n", "thinking": ""}

    calls = {"count": 0}

    async def fake_iter(**kwargs):  # noqa: ANN003
        _ = kwargs
        calls["count"] += 1
        if calls["count"] == 1:
            return False, "", "assertion failed"
        return True, "", ""

    monkeypatch.setattr(flow, "CoderAgent", FakeCoder)
    monkeypatch.setattr(flow, "adapter_for_file", lambda _f: _FakeAdapter())
    monkeypatch.setattr(flow, "_run_tdd_iteration", fake_iter)

    state = WorkingState(
        raw_idea="x",
        prd={"title": "t", "problem_statement": "p", "core_features": []},
        tech_stack={},
        file_tree={"src/": ["main.py"]},
        current_file="src/main.py",
        reasoning_config={
            "enabled": True,
            "profile": "balanced",
            "tdd_enabled": True,
            "tdd_max_iterations": 3,
            "tdd_time_split_percent": 40,
            "tdd_fail_open": True,
            "thinking_modules_enabled": True,
        },
    )
    result = asyncio.run(flow.coder_agent_node(state))
    assert result["current_code"].strip().endswith("2")
    stats = result["tdd_loop_stats"]["src/main.py"]
    assert stats["iterations"] == 2
    assert stats["enabled"] is True
