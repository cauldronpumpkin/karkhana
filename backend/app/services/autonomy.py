from __future__ import annotations

from backend.app.repository import (
    AUTONOMY_AUTONOMOUS_DEVELOPMENT,
    AUTONOMY_FULL_AUTOPILOT,
    AUTONOMY_LEVELS,
    AUTONOMY_SUGGEST_ONLY,
    FactoryRun,
)

_FORBIDDEN_OPERATIONS = frozenset({
    "deploy_to_production",
    "add_paid_service",
    "commit_secrets",
    "destructive_db_change",
})

HIGH_AUTONOMY_LEVELS = frozenset({AUTONOMY_AUTONOMOUS_DEVELOPMENT, AUTONOMY_FULL_AUTOPILOT})

OPENCODE_SERVER_REQUIRED_CAPABILITIES = frozenset({
    "permission_guard",
    "circuit_breaker",
    "litellm_proxy",
    "diff_api",
    "verification_runner",
    "graphify_update",
})

LIMITED_ENGINES = frozenset({"opencode", "openclaude", "codex"})


def get_autonomy_level(run: FactoryRun) -> str:
    return (run.config or {}).get("autonomy_level", AUTONOMY_AUTONOMOUS_DEVELOPMENT)


def validate_autonomy_level(level: str) -> str:
    if level not in AUTONOMY_LEVELS:
        raise ValueError(
            f"Invalid autonomy_level '{level}'. Must be one of: {', '.join(sorted(AUTONOMY_LEVELS))}"
        )
    return level


def can_enqueue_work(run: FactoryRun) -> bool:
    level = get_autonomy_level(run)
    return level in {AUTONOMY_AUTONOMOUS_DEVELOPMENT, AUTONOMY_FULL_AUTOPILOT}


def can_auto_advance_phase(run: FactoryRun) -> bool:
    level = get_autonomy_level(run)
    return level in {AUTONOMY_AUTONOMOUS_DEVELOPMENT, AUTONOMY_FULL_AUTOPILOT}


def can_auto_repair(run: FactoryRun) -> bool:
    level = get_autonomy_level(run)
    return level in {AUTONOMY_AUTONOMOUS_DEVELOPMENT, AUTONOMY_FULL_AUTOPILOT}


def can_bypass_repair_limits(run: FactoryRun) -> bool:
    return get_autonomy_level(run) == AUTONOMY_FULL_AUTOPILOT


def check_guardrails(run: FactoryRun, operation: str) -> None:
    if operation in _FORBIDDEN_OPERATIONS:
        raise GuardrailViolation(
            f"Operation '{operation}' is blocked by factory run guardrails. "
            f"This action requires explicit policy approval regardless of autonomy level."
        )


def validate_engine_for_autonomy_level(engine: str, autonomy_level: str) -> None:
    if autonomy_level in HIGH_AUTONOMY_LEVELS and engine in LIMITED_ENGINES:
        raise ValueError(
            f"Engine '{engine}' is a limited fallback mode and is not valid for "
            f"autonomy level '{autonomy_level}'. High-autonomy Factory Runs require "
            f"an opencode-server engine or equivalent that provides: "
            f"{', '.join(sorted(OPENCODE_SERVER_REQUIRED_CAPABILITIES))}."
        )


def validate_worker_capabilities_for_autonomy(
    worker_capabilities: list[str],
    autonomy_level: str,
    *,
    worker_name: str = "unknown",
) -> list[str]:
    missing: list[str] = []
    if autonomy_level in HIGH_AUTONOMY_LEVELS:
        for cap in OPENCODE_SERVER_REQUIRED_CAPABILITIES:
            if cap not in worker_capabilities:
                missing.append(cap)
    return missing


class GuardrailViolation(Exception):
    pass


AUTONOMY_DESCRIPTIONS = {
    AUTONOMY_SUGGEST_ONLY: {
        "label": "Suggest Only",
        "short": "Creates tasks and prompts without executing them.",
        "long": (
            "The factory run generates structured tasks, prompts, and worker contracts "
            "but does not enqueue them for automatic execution. Every step requires "
            "explicit human approval before a worker picks it up."
        ),
        "behaviors": {
            "enqueue_work": False,
            "auto_advance": False,
            "auto_repair": False,
            "bypass_limits": False,
        },
    },
    AUTONOMY_AUTONOMOUS_DEVELOPMENT: {
        "label": "Autonomous Development",
        "short": "Queues local worker tasks and repairs within configured limits.",
        "long": (
            "The factory run enqueues work items for local workers, automatically advances "
            "through phases, and attempts automated repairs on failures. Repairs are "
            "bounded by max_repair_attempts_per_task and max_repair_attempts_per_batch "
            "from project settings. Exceeding limits blocks the run for human review."
        ),
        "behaviors": {
            "enqueue_work": True,
            "auto_advance": True,
            "auto_repair": True,
            "bypass_limits": False,
        },
    },
    AUTONOMY_FULL_AUTOPILOT: {
        "label": "Full Autopilot",
        "short": "Broader automatic continuation within explicit safety guardrails.",
        "long": (
            "The factory run automatically advances through all phases and attempts "
            "repairs beyond the standard limits. Safety guardrails are always enforced: "
            "no silent production deploys, no adding paid services, no committing secrets, "
            "and no destructive database changes. These guardrails cannot be overridden "
            "by autonomy level alone."
        ),
        "behaviors": {
            "enqueue_work": True,
            "auto_advance": True,
            "auto_repair": True,
            "bypass_limits": True,
        },
    },
}
