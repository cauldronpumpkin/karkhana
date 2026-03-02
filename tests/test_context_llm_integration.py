"""Integration-like tests for BaseAgent context compaction path."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src.agents.base import BaseAgent
from src.command_center.models import ContextCompactionConfig
from src.llm.context_manager import ContextManager


class _DummyCompletions:
    async def create(self, **kwargs):
        _ = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])


class _DummyChat:
    def __init__(self):
        self.completions = _DummyCompletions()


class _DummyClient:
    def __init__(self):
        self.chat = _DummyChat()


def test_base_agent_triggers_compaction_with_job_override() -> None:
    manager = ContextManager.get()
    manager.set_global_defaults(ContextCompactionConfig(context_limit_tk=128, trigger_fill_percent=90, target_fill_percent=40))
    manager.set_job_config(
        "job-llm-context",
        use_global_defaults=False,
        override=ContextCompactionConfig(
            context_limit_tk=1,
            trigger_fill_percent=30,
            target_fill_percent=18,
            min_messages_to_compact=3,
            cooldown_calls=0,
        ),
    )

    asyncio.run(manager.initialize_job("job-llm-context", "Create API and dashboard"))

    agent = BaseAgent(job_id="job-llm-context")
    agent.client = _DummyClient()
    agent.set_runtime_context(job_id="job-llm-context", stage="coder_agent", context_type="coding_artifact")

    for _ in range(6):
        asyncio.run(agent.generate([{"role": "user", "content": "y" * 900}], temperature=0.1))

    usage = manager.get_usage_snapshot("job-llm-context")
    assert usage.compaction_count >= 1
    assert usage.fill_percent < 30
    compactions = manager.list_compactions("job-llm-context")
    assert len(compactions) >= 1
