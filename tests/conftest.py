"""Pytest fixtures for isolated Command Center tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_command_center_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Use a temporary sqlite DB and reset global singletons for every test."""
    from src.command_center import db as db_module
    from src.command_center import repository as repository_module
    from src.command_center import service as service_module
    from src.config import config
    from src.dashboard.event_bus import EventBus
    from src.llm.context_manager import ContextManager

    test_db = tmp_path / "karkhana_test.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_db, raising=True)

    prev_enabled = bool(config.agent_comms.enabled)
    prev_max_rounds = int(config.agent_comms.max_rounds)
    prev_escalate_blocking_only = bool(config.agent_comms.escalate_blocking_only)
    config.agent_comms.enabled = False
    config.agent_comms.max_rounds = 8
    config.agent_comms.escalate_blocking_only = True

    repository_module._repository = None
    service_module.CommandCenterService._instance = None
    EventBus.reset()
    ContextManager.reset()

    yield

    repository_module._repository = None
    service_module.CommandCenterService._instance = None
    EventBus.reset()
    ContextManager.reset()
    config.agent_comms.enabled = prev_enabled
    config.agent_comms.max_rounds = prev_max_rounds
    config.agent_comms.escalate_blocking_only = prev_escalate_blocking_only
