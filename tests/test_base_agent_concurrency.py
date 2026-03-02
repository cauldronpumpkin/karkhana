"""Tests for BaseAgent concurrency guard behavior."""

from __future__ import annotations

import asyncio

from src.agents.base import BaseAgent
from src.config import config


def test_base_agent_uses_semaphore_with_configured_capacity() -> None:
    assert isinstance(BaseAgent._llm_semaphore, asyncio.Semaphore)
    assert BaseAgent._llm_semaphore._value == int(config.lm_studio.max_concurrency)


def test_semaphore_serializes_when_capacity_one() -> None:
    sem = asyncio.Semaphore(1)
    order: list[str] = []

    async def worker(name: str) -> None:
        async with sem:
            order.append(f"{name}:enter")
            await asyncio.sleep(0.01)
            order.append(f"{name}:exit")

    async def _run() -> None:
        await asyncio.gather(worker("a"), worker("b"))

    asyncio.run(_run())
    assert order[0] == "a:enter"
    assert order[1] == "a:exit"
    assert order[2] == "b:enter"
    assert order[3] == "b:exit"
