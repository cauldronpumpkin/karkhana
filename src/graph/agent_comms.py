"""Agent communication routing, dedupe, and resolution helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


PM_AGENT = "pm_agent"
ARCHITECT_AGENT = "architect_agent"
REVIEWER_AGENT = "reviewer_agent"
TASKMASTER_AGENT = "taskmaster"


def normalize_request(request: Mapping[str, Any], *, default_from_agent: str) -> dict[str, Any]:
    """Normalize request shape emitted by runtime agents."""
    content = request.get("content_json", request.get("content", {})) or {}
    if not isinstance(content, dict):
        content = {"raw": str(content)}

    normalized = {
        "from_agent": str(request.get("from_agent") or default_from_agent),
        "message_type": str(request.get("message_type") or "clarification_request"),
        "topic": str(request.get("topic") or "general"),
        "content_json": content,
        "blocking": bool(request.get("blocking", False)),
    }
    return normalized


def _content_for_key(content: Mapping[str, Any]) -> dict[str, Any]:
    """Remove transient decision fields before dedupe fingerprinting."""
    cleaned = dict(content)
    cleaned.pop("decision", None)
    cleaned.pop("decision_history", None)
    return cleaned


def request_fingerprint(request: Mapping[str, Any]) -> str:
    """Generate a deterministic dedupe key for a request/message."""
    content = request.get("content_json", request.get("content", {})) or {}
    if not isinstance(content, dict):
        content = {"raw": str(content)}
    payload = {
        "from_agent": request.get("from_agent"),
        "to_agent": request.get("to_agent"),
        "message_type": request.get("message_type"),
        "topic": request.get("topic"),
        "content_json": _content_for_key(content),
    }
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return digest


def is_duplicate_request(
    request: Mapping[str, Any],
    pending_requests: list[Mapping[str, Any]],
    resolved_requests: list[Mapping[str, Any]],
) -> bool:
    """Check whether this request has already been observed."""
    needle = request_fingerprint(request)
    haystack = pending_requests + resolved_requests
    for existing in haystack:
        if str(existing.get("dedupe_key", "")) == needle:
            return True
        if request_fingerprint(existing) == needle:
            return True
    return False


def route_request_targets(
    message_type: str,
    topic: str,
    content_json: Mapping[str, Any] | None = None,
) -> list[str]:
    """Route target agents based on message type and semantic area."""
    content = dict(content_json or {})
    message_type = message_type.strip().lower()
    topic = topic.strip().lower()

    if message_type == "clarification_request":
        area = str(content.get("area") or content.get("scope") or "").strip().lower()
        if area in {"requirements", "user_intent", "product", "scope"}:
            return [PM_AGENT]
        if area in {"architecture", "constraints", "stack"}:
            return [ARCHITECT_AGENT]
        if any(token in topic for token in ("arch", "stack", "constraint")):
            return [ARCHITECT_AGENT]
        return [PM_AGENT]

    if message_type == "dependency_approval_request":
        targets = [ARCHITECT_AGENT]
        security_concern = bool(content.get("security_concern", False))
        security_text = json.dumps(content, default=str).lower()
        if security_concern or any(token in security_text for token in ("cve", "security", "vulnerability", "unsafe")):
            targets.append(REVIEWER_AGENT)
        return targets

    if message_type == "feature_change_request":
        return [PM_AGENT]

    return [PM_AGENT]


def build_agent_decision(message: Mapping[str, Any], *, state_context: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Produce a deterministic decision for a routed request.

    Returns None when the request remains unresolved and should retry/escalate.
    """
    content = dict(message.get("content_json") or {})
    if bool(content.get("force_unresolved")):
        return None

    message_type = str(message.get("message_type", "")).lower()
    to_agent = str(message.get("to_agent", "")).lower()
    topic = str(message.get("topic", "general"))
    context = dict(state_context or {})

    if message_type == "clarification_request":
        if to_agent == PM_AGENT:
            title = ""
            prd = context.get("prd")
            if isinstance(prd, dict):
                title = str(prd.get("title", "")).strip()
            rationale = "PM clarified requirements scope."
            if title:
                rationale = f"PM clarified requirements for '{title}'."
            return {
                "status": "approved",
                "rationale": rationale,
                "metadata": {"resolved_by": PM_AGENT, "topic": topic},
            }
        if to_agent == ARCHITECT_AGENT:
            return {
                "status": "approved",
                "rationale": "Architect provided architecture constraints guidance.",
                "metadata": {"resolved_by": ARCHITECT_AGENT, "topic": topic},
            }
        if to_agent == TASKMASTER_AGENT:
            return {
                "status": "approved",
                "rationale": "Taskmaster clarified sequencing and decomposition.",
                "metadata": {"resolved_by": TASKMASTER_AGENT, "topic": topic},
            }
        return None

    if message_type == "dependency_approval_request":
        dependency_name = str(
            content.get("dependency_name") or content.get("dependency") or topic
        ).strip()
        lowered = dependency_name.lower()
        risky = bool(content.get("security_concern")) or any(
            token in lowered for token in ("eval", "pickle", "shell", "exec")
        )

        if to_agent == REVIEWER_AGENT:
            if risky:
                return {
                    "status": "rejected",
                    "rationale": f"Reviewer rejected risky dependency '{dependency_name}'.",
                    "metadata": {"resolved_by": REVIEWER_AGENT, "dependency": dependency_name},
                }
            return {
                "status": "approved",
                "rationale": f"Reviewer approved dependency '{dependency_name}'.",
                "metadata": {"resolved_by": REVIEWER_AGENT, "dependency": dependency_name},
            }

        if to_agent == ARCHITECT_AGENT:
            if risky:
                return {
                    "status": "rejected",
                    "rationale": f"Architect rejected risky dependency '{dependency_name}'.",
                    "metadata": {"resolved_by": ARCHITECT_AGENT, "dependency": dependency_name},
                }
            return {
                "status": "approved",
                "rationale": f"Architect approved dependency '{dependency_name}'.",
                "metadata": {"resolved_by": ARCHITECT_AGENT, "dependency": dependency_name},
            }
        return None

    if message_type == "feature_change_request":
        requested = str(content.get("requested_change") or topic).lower()
        if to_agent == PM_AGENT:
            if "out of scope" in requested:
                return {
                    "status": "rejected",
                    "rationale": "PM rejected feature change as out of scope.",
                    "metadata": {"resolved_by": PM_AGENT},
                }
            return {
                "status": "approved",
                "rationale": "PM approved feature change request.",
                "metadata": {"resolved_by": PM_AGENT},
            }
        return None

    return None
