"""Tests for CoderAgent tool-calling integration."""

from __future__ import annotations

import asyncio

from src.agents.coder_agent import CoderAgent
from src.config import config


def test_write_file_passes_tools_when_enabled(monkeypatch) -> None:
    prev_enabled = bool(config.tool_calling.enabled)
    config.tool_calling.enabled = True
    try:
        agent = CoderAgent()
        captured: dict = {}

        async def fake_generate(messages, temperature=0.2, **kwargs):  # noqa: ANN001, ANN202
            _ = messages
            captured["temperature"] = temperature
            captured.update(kwargs)
            return "print('ok')"

        monkeypatch.setattr(agent, "generate", fake_generate)

        result = asyncio.run(
            agent.write_file(
                file_path="src/main.py",
                prd_context={"title": "T", "problem_statement": "P"},
                tech_stack={},
                requirements=["Implement main flow"],
                existing_files={"README.md": "hello"},
            )
        )
        assert result["code"] == "print('ok')"
        assert captured["tools"]
        tool_names = sorted(t["function"]["name"] for t in captured["tools"])
        assert tool_names == ["list_files", "read_file"]
        assert "list_files" in captured["tool_handlers"]
        assert "read_file" in captured["tool_handlers"]
    finally:
        config.tool_calling.enabled = prev_enabled


def test_write_file_omits_tools_when_disabled(monkeypatch) -> None:
    prev_enabled = bool(config.tool_calling.enabled)
    config.tool_calling.enabled = False
    try:
        agent = CoderAgent()
        captured: dict = {}

        async def fake_generate(messages, temperature=0.2, **kwargs):  # noqa: ANN001, ANN202
            _ = messages
            captured["temperature"] = temperature
            captured.update(kwargs)
            return "print('ok')"

        monkeypatch.setattr(agent, "generate", fake_generate)
        result = asyncio.run(
            agent.write_file(
                file_path="src/main.py",
                prd_context={"title": "T", "problem_statement": "P"},
                tech_stack={},
                requirements=["Implement main flow"],
                existing_files={"README.md": "hello"},
            )
        )
        assert result["code"] == "print('ok')"
        assert "tools" not in captured
        assert "tool_handlers" not in captured
    finally:
        config.tool_calling.enabled = prev_enabled


def test_read_file_tool_respects_truncation_limit() -> None:
    prev_limit = int(config.tool_calling.file_tool_max_chars)
    try:
        config.tool_calling.file_tool_max_chars = 5
        agent = CoderAgent()
        _tools, handlers = agent._build_file_tools({"src/main.py": "123456789"})
        payload = handlers["read_file"]({"path": "src/main.py"})
        assert payload["ok"] is True
        assert payload["content"] == "12345"
        assert payload["truncated"] is True
        assert payload["total_chars"] == 9
    finally:
        config.tool_calling.file_tool_max_chars = prev_limit
