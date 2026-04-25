"""Test fixtures for Idea Refinery backend tests."""
from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.repository import (
    Idea,
    IdeaRelationship,
    InMemoryRepository,
    Message,
    PhaseRecord,
    ProjectMemory,
    Report,
    ResearchTask,
    Score,
    set_repository,
)


class MockLLMService:
    """Mock LLM service that returns canned responses."""

    def __init__(self, responses: dict | None = None) -> None:
        self.responses = responses or {}
        self.default_response = "Mock response"
        self.call_history: list[list[dict]] = []

    async def chat_completion_sync(self, messages: list[dict]) -> str:
        self.call_history.append(messages)
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break
        for key, value in self.responses.items():
            if key in user_content:
                return value
        return self.default_response

    async def chat_completion(self, messages: list[dict], stream: bool = True):
        self.call_history.append(messages)
        response = self.default_response
        for chunk in response.split(" "):
            yield chunk + " "


class FakeSession:
    def __init__(self, repo: InMemoryRepository) -> None:
        self.repo = repo
        self._pending: list[object] = []

    def add(self, item: object) -> None:
        self._pending.append(item)

    def add_all(self, items: list[object]) -> None:
        self._pending.extend(items)

    async def commit(self) -> None:
        for item in self._pending:
            if isinstance(item, Idea):
                await self.repo.create_idea(item)
            elif isinstance(item, Score):
                await self.repo.put_score(item)
            elif isinstance(item, Message):
                await self.repo.add_message(item)
            elif isinstance(item, ProjectMemory):
                await self.repo.upsert_memory(item)
            elif isinstance(item, PhaseRecord):
                await self.repo.add_phase_record(item)
            elif isinstance(item, ResearchTask):
                await self.repo.add_research_task(item)
            elif isinstance(item, Report):
                await self.repo.put_report(item)
            elif isinstance(item, IdeaRelationship):
                await self.repo.add_relationship(item)
        self._pending.clear()

    async def refresh(self, item: object) -> None:
        return None


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[FakeSession, None]:
    repo = InMemoryRepository()
    set_repository(repo)
    yield FakeSession(repo)
    set_repository(InMemoryRepository())


@pytest_asyncio.fixture
async def test_client(db_session: FakeSession) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_llm() -> MockLLMService:
    return MockLLMService()


@pytest_asyncio.fixture
async def sample_idea(db_session: FakeSession) -> Idea:
    idea = Idea(
        id="test-idea-001",
        title="Test Idea",
        slug="test-idea",
        description="A test idea for unit testing",
        current_phase="capture",
        status="active",
    )
    db_session.add(idea)
    await db_session.commit()
    return idea


@pytest_asyncio.fixture
async def sample_idea_two(db_session: FakeSession) -> Idea:
    idea = Idea(
        id="test-idea-002",
        title="Second Idea",
        slug="second-idea",
        description="Another test idea for relationship testing",
        current_phase="clarify",
        status="active",
    )
    db_session.add(idea)
    await db_session.commit()
    return idea


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)
