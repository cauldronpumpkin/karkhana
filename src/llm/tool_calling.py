"""Helpers for parsing local-model fallback tool-call payloads."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any


def parse_fallback_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse tool calls from local-model text output."""
    if not isinstance(text, str) or not text.strip():
        return []

    candidates: list[Any] = []
    tagged_blocks = re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, flags=re.DOTALL | re.IGNORECASE)
    for block in tagged_blocks:
        parsed = _parse_json(block.strip())
        if parsed is not None:
            candidates.append(parsed)

    if not candidates:
        parsed_full = _parse_json(text.strip())
        if parsed_full is not None:
            candidates.append(parsed_full)
        else:
            candidates.extend(_extract_json_fragments(text))

    normalized: list[dict[str, Any]] = []
    for candidate in candidates:
        normalized.extend(_normalize_candidate(candidate))

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for call in normalized:
        dedupe_key = json.dumps(
            {
                "id": call.get("id"),
                "name": call.get("name"),
                "arguments": call.get("arguments"),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(call)
    return deduped


def _parse_json(text: str) -> Any | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_json_fragments(text: str) -> list[Any]:
    decoder = json.JSONDecoder()
    parsed: list[Any] = []
    i = 0
    while i < len(text):
        if text[i] not in "{[":
            i += 1
            continue
        try:
            value, end = decoder.raw_decode(text[i:])
        except Exception:
            i += 1
            continue
        parsed.append(value)
        i += max(1, end)
    return parsed


def _normalize_candidate(candidate: Any) -> list[dict[str, Any]]:
    if isinstance(candidate, list):
        calls: list[dict[str, Any]] = []
        for item in candidate:
            calls.extend(_normalize_candidate(item))
        return calls

    if not isinstance(candidate, dict):
        return []

    maybe_call = _to_call(candidate)
    if maybe_call:
        return [maybe_call]

    # Some models nest the call envelope inside a top-level wrapper.
    nested_calls: list[dict[str, Any]] = []
    for value in candidate.values():
        nested_calls.extend(_normalize_candidate(value))
    return nested_calls


def _to_call(payload: dict[str, Any]) -> dict[str, Any] | None:
    name = payload.get("name") or payload.get("tool") or payload.get("tool_name")
    arguments = payload.get("arguments", payload.get("args", payload.get("parameters", {})))

    function = payload.get("function")
    if isinstance(function, dict):
        name = name or function.get("name")
        arguments = function.get("arguments", function.get("args", arguments))
    elif isinstance(function, str) and not name:
        name = function

    if not isinstance(name, str) or not name.strip():
        return None

    parsed_args = _normalize_arguments(arguments)
    call_id = payload.get("id")
    if not isinstance(call_id, str) or not call_id.strip():
        call_id = f"fallback_{uuid.uuid4().hex[:10]}"

    return {
        "id": call_id,
        "name": name.strip(),
        "arguments": parsed_args,
    }


def _normalize_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if arguments is None:
        return {}
    if isinstance(arguments, str):
        text = arguments.strip()
        if not text:
            return {}
        parsed = _parse_json(text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "__parse_error__": "invalid_json_arguments",
            "_raw": arguments,
        }
    if isinstance(arguments, (int, float, bool)):
        return {"value": arguments}
    if isinstance(arguments, list):
        return {"items": arguments}
    return {"_raw": str(arguments)}
