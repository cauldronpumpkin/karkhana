"""Deterministic parser for slash commands and natural-language intents."""

from __future__ import annotations

import re
import shlex
from typing import Any

from src.command_center.models import ParsedCommand


HELP_TEXT = (
    "Supported commands: /run [--approval on|off] [--reasoning on|off] "
    "[--profile fast|balanced|deep] [--tot-paths N] [--critic on|off] "
    "[--tdd on|off] [--tdd-split P] [--thinking on|off] [--thinking-logs on|off] <idea>, /jobs, /job <id>, "
    "/logs <id>, /stop <id>, /approve <id> [stage], /help"
)


def parse_chat_message(message: str, active_job_id: str | None = None) -> ParsedCommand:
    """Parse chat input into an executable command."""
    text = message.strip()
    if not text:
        return ParsedCommand(action="help", ok=False, error=HELP_TEXT)

    if text.startswith("/"):
        return _parse_slash(text)
    return _parse_intent(text, active_job_id=active_job_id)


def _parse_slash(text: str) -> ParsedCommand:
    lower = text.lower()
    if lower == "/help":
        return ParsedCommand(action="help", args={"message": HELP_TEXT})
    if lower == "/jobs":
        return ParsedCommand(action="jobs")

    match = re.match(r"^/job\s+([a-zA-Z0-9_-]+)\s*$", text)
    if match:
        return ParsedCommand(action="job", args={"job_id": match.group(1)})

    match = re.match(r"^/logs\s+([a-zA-Z0-9_-]+)\s*$", text)
    if match:
        return ParsedCommand(action="logs", args={"job_id": match.group(1)})

    match = re.match(r"^/stop\s+([a-zA-Z0-9_-]+)\s*$", text)
    if match:
        return ParsedCommand(action="stop", args={"job_id": match.group(1)})

    match = re.match(r"^/approve\s+([a-zA-Z0-9_-]+)(?:\s+([a-zA-Z0-9_.-]+))?\s*$", text)
    if match:
        return ParsedCommand(action="approve", args={"job_id": match.group(1), "stage": match.group(2)})

    if lower.startswith("/run"):
        return _parse_run_command(text)

    return ParsedCommand(action="help", ok=False, error=f"Unknown command. {HELP_TEXT}")


def _parse_intent(text: str, active_job_id: str | None = None) -> ParsedCommand:
    lower = text.lower().strip()

    if any(k in lower for k in ("help", "commands", "what can you do")):
        return ParsedCommand(action="help", args={"message": HELP_TEXT})

    if lower.startswith("run ") or lower.startswith("start "):
        idea = re.sub(r"^(run|start)\s+", "", text, flags=re.IGNORECASE).strip()
        if not idea:
            return ParsedCommand(action="help", ok=False, error="Please provide an idea to run.")
        approval_required = "approval on" in lower or "with approval" in lower
        return ParsedCommand(action="run", args={"idea": idea, "approval_required": approval_required})

    if any(k in lower for k in ("list jobs", "show jobs", "job list", "status of jobs")):
        return ParsedCommand(action="jobs")

    stop_match = re.search(r"(?:stop|cancel)\s+([a-zA-Z0-9_-]{6,})", lower)
    if stop_match:
        return ParsedCommand(action="stop", args={"job_id": stop_match.group(1)})
    if any(k in lower for k in ("stop current", "cancel current")) and active_job_id:
        return ParsedCommand(action="stop", args={"job_id": active_job_id})

    log_match = re.search(r"(?:logs|log)\s+(?:for\s+)?([a-zA-Z0-9_-]{6,})", lower)
    if log_match:
        return ParsedCommand(action="logs", args={"job_id": log_match.group(1)})
    if "logs" in lower and active_job_id:
        return ParsedCommand(action="logs", args={"job_id": active_job_id})

    approve_match = re.search(r"(?:approve|resume)\s+([a-zA-Z0-9_-]{6,})(?:\s+([a-zA-Z0-9_.-]+))?", lower)
    if approve_match:
        return ParsedCommand(
            action="approve",
            args={"job_id": approve_match.group(1), "stage": approve_match.group(2)},
        )
    if any(k in lower for k in ("approve current", "resume current")) and active_job_id:
        return ParsedCommand(action="approve", args={"job_id": active_job_id, "stage": None})

    job_match = re.search(r"(?:job|status)\s+([a-zA-Z0-9_-]{6,})", lower)
    if job_match:
        return ParsedCommand(action="job", args={"job_id": job_match.group(1)})

    return ParsedCommand(action="help", ok=False, error=f"I couldn't map that request. {HELP_TEXT}")


def _parse_on_off(value: str | None, *, default: bool | None = None) -> bool | None:
    if value is None:
        return default
    v = value.strip().lower()
    if v == "on":
        return True
    if v == "off":
        return False
    return default


def _parse_run_command(text: str) -> ParsedCommand:
    try:
        tokens = shlex.split(text)
    except ValueError:
        return ParsedCommand(action="help", ok=False, error="Invalid /run command syntax.")

    if not tokens or tokens[0].lower() != "/run":
        return ParsedCommand(action="help", ok=False, error=HELP_TEXT)

    approval_required = False
    reasoning: dict[str, Any] = {}
    idea_tokens: list[str] = []

    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--approval" and i + 1 < len(tokens):
            approval_required = bool(_parse_on_off(tokens[i + 1], default=False))
            i += 2
            continue
        if tok == "--reasoning" and i + 1 < len(tokens):
            val = _parse_on_off(tokens[i + 1], default=None)
            if val is not None:
                reasoning["enabled"] = val
            i += 2
            continue
        if tok == "--profile" and i + 1 < len(tokens):
            reasoning["profile"] = tokens[i + 1].strip().lower()
            i += 2
            continue
        if tok == "--tot-paths" and i + 1 < len(tokens):
            try:
                reasoning["architect_tot_paths"] = int(tokens[i + 1])
            except ValueError:
                pass
            i += 2
            continue
        if tok == "--critic" and i + 1 < len(tokens):
            val = _parse_on_off(tokens[i + 1], default=None)
            if val is not None:
                reasoning["critic_enabled"] = val
            i += 2
            continue
        if tok == "--tdd" and i + 1 < len(tokens):
            val = _parse_on_off(tokens[i + 1], default=None)
            if val is not None:
                reasoning["tdd_enabled"] = val
            i += 2
            continue
        if tok == "--tdd-split" and i + 1 < len(tokens):
            try:
                reasoning["tdd_time_split_percent"] = int(tokens[i + 1])
            except ValueError:
                pass
            i += 2
            continue
        if tok == "--thinking" and i + 1 < len(tokens):
            val = _parse_on_off(tokens[i + 1], default=None)
            if val is not None:
                reasoning["thinking_modules_enabled"] = val
            i += 2
            continue
        if tok == "--thinking-logs" and i + 1 < len(tokens):
            val = _parse_on_off(tokens[i + 1], default=None)
            if val is not None:
                reasoning["thinking_visibility"] = "logs" if val else "internal"
            i += 2
            continue

        idea_tokens = tokens[i:]
        break

    idea = " ".join(idea_tokens).strip()
    if not idea:
        return ParsedCommand(action="help", ok=False, error="Please provide an idea to run.")

    args: dict[str, Any] = {"idea": idea, "approval_required": approval_required}
    if reasoning:
        args["reasoning"] = reasoning
    return ParsedCommand(action="run", args=args)


def command_to_response_payload(command: ParsedCommand) -> dict[str, Any]:
    """Utility for debugging responses."""
    return {"action": command.action, "ok": command.ok, "args": command.args, "error": command.error}
