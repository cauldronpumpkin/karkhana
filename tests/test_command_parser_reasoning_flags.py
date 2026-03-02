"""Parser tests for /run reasoning flags."""

from __future__ import annotations

from src.command_center.parser import parse_chat_message


def test_run_command_parses_reasoning_flags() -> None:
    cmd = parse_chat_message(
        "/run --approval on --reasoning on --profile deep --tot-paths 5 "
        "--critic off --tdd on --tdd-split 55 --thinking on --thinking-logs on Build AI IDE"
    )
    assert cmd.ok is True
    assert cmd.action == "run"
    assert cmd.args["idea"] == "Build AI IDE"
    assert cmd.args["approval_required"] is True
    reasoning = cmd.args["reasoning"]
    assert reasoning["enabled"] is True
    assert reasoning["profile"] == "deep"
    assert reasoning["architect_tot_paths"] == 5
    assert reasoning["critic_enabled"] is False
    assert reasoning["tdd_enabled"] is True
    assert reasoning["tdd_time_split_percent"] == 55
    assert reasoning["thinking_modules_enabled"] is True
    assert reasoning["thinking_visibility"] == "logs"
