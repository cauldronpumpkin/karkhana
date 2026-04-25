"""Test server entry point with mocked LLM service.

This module patches all LLM calls to return deterministic mock responses,
allowing E2E tests to run without real API keys or network calls.
"""
from __future__ import annotations

import json
import sys
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

# Patch LLMService BEFORE importing ANYTHING from the app
from backend.app.services import llm as llm_module


def _mock_llm_init(self, *args, **kwargs):
    """Replace LLMService init to avoid real API connections."""
    self.client = MagicMock()
    self.provider = "mock"
    self.model = "mock-model"


async def _mock_chat_completion(
    self,
    messages: list,
    stream: bool = True,
    provider: str | None = None,
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Mock streaming chat completion."""
    yield "This is a mock LLM response for E2E testing."


async def _mock_chat_completion_sync(
    self,
    messages: list,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Mock synchronous chat completion."""
    # Return different responses based on context
    system_msg = messages[0].get("content", "").lower() if messages else ""

    if "research strategist" in system_msg:
        return '[{"topic": "Market Analysis", "prompt": "Analyze the market for this idea."}]'
    elif "research integration" in system_msg or "read this research" in system_msg:
        return "Mock research integration summary with key insights."
    elif "score" in system_msg or "dimension" in system_msg:
        return json.dumps({
            "tam": {"value": 8.0, "rationale": "Large market opportunity"},
            "competition": {"value": 7.0, "rationale": "Moderate competition"},
            "feasibility": {"value": 7.5, "rationale": "Technically feasible"},
            "time_to_mvp": {"value": 8.0, "rationale": "Quick to MVP"},
            "revenue": {"value": 7.0, "rationale": "Clear revenue model"},
            "uniqueness": {"value": 6.5, "rationale": "Somewhat unique"},
            "personal_fit": {"value": 8.0, "rationale": "Good personal fit"},
        })
    elif "prometheus" in system_msg or "software architect" in system_msg:
        return "# Mock Prometheus Planning Prompt\n\nThis is a mock build planning prompt for E2E testing."
    elif "implementation prompt" in system_msg or "step" in system_msg:
        return "Mock step implementation prompt for E2E testing."
    elif "evaluate" in system_msg or "advance" in system_msg:
        return '{"ready": true, "reasoning": "Mock: sufficient information to advance.", "next_phase": "clarify"}'
    elif "generate a comprehensive summary report" in system_msg:
        return "# Mock Phase Report\n\nMock phase report content for E2E testing."
    elif "relationship" in system_msg or "related" in system_msg:
        return "[]"
    else:
        return "This is a mock LLM response for E2E testing."


async def _mock_list_providers(self, discover: bool = True) -> list[dict]:
    return [
        {
            "id": "mock",
            "name": "Mock Provider",
            "base_url": "http://test",
            "configured": True,
            "default_model": "mock-model",
            "models": ["mock-model"],
            "models_source": "configured",
        }
    ]


def _mock_get_provider(self, provider: str | None = None) -> dict:
    return {"provider": "mock", "provider_name": "Mock Provider", "model": "mock-model"}


# Apply patches to the class BEFORE any app imports
llm_module.LLMService.__init__ = _mock_llm_init
llm_module.LLMService.chat_completion = _mock_chat_completion
llm_module.LLMService.chat_completion_sync = _mock_chat_completion_sync
llm_module.LLMService.list_providers = _mock_list_providers
llm_module.LLMService.get_provider = _mock_get_provider

# Now import the app
from backend.app.main import app  # noqa: E402, F402
from backend.app.database import engine
from backend.app.models.base import Base  # noqa: E402

# Drop and recreate all database tables on startup for clean test state
@app.on_event("startup")
async def test_startup():
    """Drop and recreate database tables for clean test state."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

# Patch the chat router's module-level llm_service instance
# (it was created during import of main.py, so we need to patch the instance directly)
from backend.app.routers import ai as ai_router  # noqa: E402
from backend.app.routers import chat as chat_router  # noqa: E402
chat_router.llm_service.client = MagicMock()
chat_router.llm_service.provider = "mock"
chat_router.llm_service.model = "mock-model"
ai_router.llm_service.client = MagicMock()
ai_router.llm_service.provider = "mock"
ai_router.llm_service.model = "mock-model"
# Bind methods to the instance using types.MethodType
import types
chat_router.llm_service.chat_completion = types.MethodType(_mock_chat_completion, chat_router.llm_service)
chat_router.llm_service.chat_completion_sync = types.MethodType(_mock_chat_completion_sync, chat_router.llm_service)
ai_router.llm_service.list_providers = types.MethodType(_mock_list_providers, ai_router.llm_service)
ai_router.llm_service.get_provider = types.MethodType(_mock_get_provider, ai_router.llm_service)
