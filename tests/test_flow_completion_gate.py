"""Tests that completed_files is gated on sandbox success."""

from __future__ import annotations

import asyncio

from src.graph import flow
from src.types.state import WorkingState


class _FakeAdapter:
    def available(self) -> bool:
        return True

    def generate_syntax_command(self, *, file_path: str) -> list[str]:
        _ = file_path
        return ["echo", "ok"]


def test_completed_files_set_only_after_sandbox_pass(monkeypatch) -> None:
    class FakeCoder:
        def set_runtime_context(self, **kwargs):  # noqa: ANN003
            _ = kwargs

        def generate_coordination_requests(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            return []

        async def write_file(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            return {"code": "print('ok')", "thinking": ""}

    async def fake_execute(self, command, cwd):  # noqa: ANN001, ANN201
        _ = (self, command, cwd)
        return 0, "ok", ""

    monkeypatch.setattr(flow, "CoderAgent", FakeCoder)
    monkeypatch.setattr(flow, "adapter_for_file", lambda _f: _FakeAdapter())
    monkeypatch.setattr(flow.SandboxExecutor, "execute", fake_execute)

    state = WorkingState(
        raw_idea="x",
        prd={"title": "t", "problem_statement": "p", "core_features": []},
        file_tree={"src/": ["main.py"]},
        current_file="src/main.py",
        reasoning_config={"enabled": False},
    )
    coder_out = asyncio.run(flow.coder_agent_node(state))
    assert "completed_files" not in coder_out

    sandbox_state = state.model_copy(update=coder_out)
    sandbox_out = asyncio.run(flow.sandbox_executor_node(sandbox_state))
    assert "src/main.py" in sandbox_out["completed_files"]
