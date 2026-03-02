"""Unit tests for context compaction manager behavior."""

from __future__ import annotations

import asyncio

from src.command_center.models import ContextCompactionConfig
from src.llm.context_manager import ContextManager


def test_compaction_reduces_below_target_fill() -> None:
    manager = ContextManager.get()
    cfg = ContextCompactionConfig(
        context_limit_tk=1,
        trigger_fill_percent=30,
        target_fill_percent=20,
        min_messages_to_compact=3,
        cooldown_calls=0,
    )
    manager.set_global_defaults(cfg)

    job_id = "job-compaction"
    asyncio.run(manager.initialize_job(job_id, "Build a coding assistant"))

    for _ in range(8):
        asyncio.run(
            manager.prepare_messages(
                job_id,
                [{"role": "user", "content": "x" * 700}],
                stage="coder_agent",
                context_type="coding_artifact",
            )
        )

    usage = manager.get_usage_snapshot(job_id)
    assert usage.fill_percent < cfg.trigger_fill_percent
    assert usage.compaction_count >= 1
    assert usage.last_summary_text


def test_job_override_precedence_over_global_defaults() -> None:
    manager = ContextManager.get()
    manager.set_global_defaults(ContextCompactionConfig(context_limit_tk=128, trigger_fill_percent=90, target_fill_percent=40))

    override = ContextCompactionConfig(context_limit_tk=2, trigger_fill_percent=55, target_fill_percent=30)
    manager.set_job_config("job-override", use_global_defaults=False, override=override)

    effective = manager.get_effective_config("job-override")
    assert effective.context_limit_tk == 2
    assert effective.trigger_fill_percent == 55
    assert effective.target_fill_percent == 30
