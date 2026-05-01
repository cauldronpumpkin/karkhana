from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.app.config import settings
from backend.app.repository import GitHubInstallation
from backend.app.services import github_app as github_app_module
from backend.app.services.github_app import GitHubAppService


@pytest.mark.asyncio
async def test_create_draft_pull_request_success(db_session, monkeypatch):
    repo = db_session.repo
    await repo.save_github_installation(
        GitHubInstallation(
            installation_id="inst-123",
            account_login="acme",
            status="active",
        )
    )
    _configure_github_app(monkeypatch)

    service = GitHubAppService()
    monkeypatch.setattr(service, "create_installation_token", AsyncMock(return_value="inst-token"))

    client = _FakeAsyncClient(
        httpx.Response(
            201,
            request=httpx.Request("POST", "https://api.github.com/repos/acme/repo/pulls"),
            content=(
                b'{"url":"https://api.github.com/repos/acme/repo/pulls/42",'
                b'"html_url":"https://github.com/acme/repo/pull/42",'
                b'"number":42,"state":"open","draft":true}'
            ),
            headers={"content-type": "application/json"},
        )
    )
    monkeypatch.setattr(github_app_module.httpx, "AsyncClient", lambda timeout=20: client)

    result = await service.create_draft_pull_request(
        installation_id="inst-123",
        owner="acme",
        repo_name="repo",
        title="Add worker result PR",
        head_branch="worker/result-branch",
        base_branch="main",
        body="Worker branch result",
    )

    assert result == {
        "url": "https://api.github.com/repos/acme/repo/pulls/42",
        "html_url": "https://github.com/acme/repo/pull/42",
        "number": 42,
        "state": "open",
        "draft": True,
    }
    assert client.requests == [
        {
            "method": "post",
            "url": "https://api.github.com/repos/acme/repo/pulls",
            "headers": {
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer inst-token",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            "json": {
                "title": "Add worker result PR",
                "head": "worker/result-branch",
                "base": "main",
                "body": "Worker branch result",
                "draft": True,
            },
        }
    ]


@pytest.mark.asyncio
async def test_create_draft_pull_request_requires_github_app_config(monkeypatch):
    _configure_github_app(monkeypatch, app_id="", private_key="")

    service = GitHubAppService()

    with pytest.raises(ValueError, match="GitHub App is not configured"):
        await service.create_draft_pull_request(
            installation_id="inst-123",
            owner="acme",
            repo_name="repo",
            title="Add worker result PR",
            head_branch="worker/result-branch",
            base_branch="main",
        )


@pytest.mark.asyncio
async def test_create_draft_pull_request_requires_active_installation(db_session, monkeypatch):
    _configure_github_app(monkeypatch)

    service = GitHubAppService()
    monkeypatch.setattr(service, "create_installation_token", AsyncMock(return_value="inst-token"))

    with pytest.raises(ValueError, match="GitHub installation inst-404 was not found"):
        await service.create_draft_pull_request(
            installation_id="inst-404",
            owner="acme",
            repo_name="repo",
            title="Add worker result PR",
            head_branch="worker/result-branch",
            base_branch="main",
        )


@pytest.mark.asyncio
async def test_create_draft_pull_request_wraps_http_failure(db_session, monkeypatch):
    repo = db_session.repo
    await repo.save_github_installation(
        GitHubInstallation(
            installation_id="inst-123",
            account_login="acme",
            status="active",
        )
    )
    _configure_github_app(monkeypatch)

    service = GitHubAppService()
    monkeypatch.setattr(service, "create_installation_token", AsyncMock(return_value="inst-token"))

    client = _FakeAsyncClient(
        httpx.Response(
            422,
            request=httpx.Request("POST", "https://api.github.com/repos/acme/repo/pulls"),
            content=b'{"message":"Validation Failed"}',
            headers={"content-type": "application/json"},
        )
    )
    monkeypatch.setattr(github_app_module.httpx, "AsyncClient", lambda timeout=20: client)

    with pytest.raises(RuntimeError, match=r"GitHub draft pull request creation failed \(422\):"):
        await service.create_draft_pull_request(
            installation_id="inst-123",
            owner="acme",
            repo_name="repo",
            title="Add worker result PR",
            head_branch="worker/result-branch",
            base_branch="main",
        )


def _configure_github_app(monkeypatch, app_id: str = "app-123", private_key: str = "private-key") -> None:
    monkeypatch.setattr(settings, "github_app_id", app_id)
    monkeypatch.setattr(settings, "github_app_private_key", private_key)
    monkeypatch.setattr(settings, "github_app_private_key_path", "")


class _FakeAsyncClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, url: str, headers: dict[str, str] | None = None, json: dict[str, Any] | None = None) -> httpx.Response:
        self.requests.append(
            {
                "method": "post",
                "url": url,
                "headers": headers or {},
                "json": json or {},
            }
        )
        return self.response
