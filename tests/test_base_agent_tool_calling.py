"""Tests for BaseAgent tool-calling behavior with local-model fallbacks."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from src.agents.base import BaseAgent


def _tool_response(*, name: str, arguments: str, call_id: str = "call_1"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))],
                )
            )
        ]
    )


def _text_response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None))]
    )


class _DummyCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("No fake response left for create()")
        return self._responses.pop(0)


class _DummyChat:
    def __init__(self, responses):
        self.completions = _DummyCompletions(responses)


class _DummyClient:
    def __init__(self, responses):
        self.chat = _DummyChat(responses)


def test_structured_tool_call_executes_and_returns_final_text() -> None:
    agent = BaseAgent()
    agent.client = _DummyClient(
        [
            _tool_response(name="list_files", arguments="{}"),
            _text_response("final answer"),
        ]
    )
    seen: dict[str, dict] = {}

    def list_files(args: dict) -> dict:
        seen["args"] = args
        return {"paths": ["README.md"]}

    out = asyncio.run(
        agent.generate(
            [{"role": "user", "content": "inspect files"}],
            tools=[{"type": "function", "function": {"name": "list_files"}}],
            tool_handlers={"list_files": list_files},
            max_tool_rounds=4,
            fallback_tool_parsing=True,
        )
    )

    assert out == "final answer"
    assert seen["args"] == {}
    second_messages = agent.client.chat.completions.calls[1]["messages"]
    assert any(m.get("role") == "tool" and m.get("tool_call_id") == "call_1" for m in second_messages)


def test_fallback_tool_call_parses_tagged_json() -> None:
    agent = BaseAgent()
    agent.client = _DummyClient(
        [
            _text_response('<tool_call>{"name":"read_file","arguments":{"path":"README.md"}}</tool_call>'),
            _text_response("fallback complete"),
        ]
    )
    seen: dict[str, str] = {}

    def read_file(args: dict) -> dict:
        seen["path"] = str(args.get("path"))
        return {"ok": True, "content": "stub"}

    out = asyncio.run(
        agent.generate(
            [{"role": "user", "content": "read file"}],
            tools=[{"type": "function", "function": {"name": "read_file"}}],
            tool_handlers={"read_file": read_file},
            fallback_tool_parsing=True,
        )
    )

    assert out == "fallback complete"
    assert seen["path"] == "README.md"


def test_unknown_tool_returns_error_payload_and_continues() -> None:
    agent = BaseAgent()
    agent.client = _DummyClient(
        [
            _text_response('<tool_call>{"name":"missing_tool","arguments":{"x":1}}</tool_call>'),
            _text_response("done"),
        ]
    )

    out = asyncio.run(
        agent.generate(
            [{"role": "user", "content": "call unknown"}],
            tools=[{"type": "function", "function": {"name": "read_file"}}],
            tool_handlers={"read_file": lambda args: args},
            fallback_tool_parsing=True,
        )
    )
    assert out == "done"

    second_messages = agent.client.chat.completions.calls[1]["messages"]
    tool_messages = [m for m in second_messages if m.get("role") == "tool"]
    assert tool_messages
    payload = json.loads(tool_messages[0]["content"])
    assert payload["error"] == "unknown_tool"


def test_tool_round_limit_triggers_finalization_prompt() -> None:
    agent = BaseAgent()
    agent.client = _DummyClient(
        [
            _tool_response(name="list_files", arguments="{}"),
            _tool_response(name="list_files", arguments="{}"),
            _text_response("forced final"),
        ]
    )

    out = asyncio.run(
        agent.generate(
            [{"role": "user", "content": "loop"}],
            tools=[{"type": "function", "function": {"name": "list_files"}}],
            tool_handlers={"list_files": lambda args: {"ok": True, "args": args}},
            max_tool_rounds=1,
            fallback_tool_parsing=True,
        )
    )

    assert out == "forced final"
    assert len(agent.client.chat.completions.calls) == 3
