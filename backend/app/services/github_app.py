from __future__ import annotations

import hmac
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

import httpx

from backend.app.config import settings
from backend.app.repository import GitHubInstallation, get_repository

GITHUB_API_BASE = "https://api.github.com"


class GitHubAppService:
    """GitHub App helper for installation metadata and short-lived tokens."""

    def is_configured(self) -> bool:
        try:
            self._require_configured()
        except ValueError:
            return False
        return True

    def verify_webhook_signature(self, body: bytes, signature_header: str | None) -> bool:
        if not settings.github_webhook_secret:
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        digest = hmac.new(settings.github_webhook_secret.encode("utf-8"), body, sha256).hexdigest()
        expected = f"sha256={digest}"
        return hmac.compare_digest(expected, signature_header)

    async def handle_webhook(self, event_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        repo = get_repository()
        action = payload.get("action", "")
        installation = payload.get("installation") or {}
        installation_id = str(installation.get("id") or "")
        account = installation.get("account") or payload.get("repository", {}).get("owner") or {}

        if installation_id:
            await repo.save_github_installation(
                GitHubInstallation(
                    installation_id=installation_id,
                    account_login=account.get("login") or "unknown",
                    account_type=account.get("type") or "User",
                    status="deleted" if action == "deleted" else "active",
                )
            )

        if event_name == "push":
            repository = payload.get("repository") or {}
            full_name = repository.get("full_name")
            after = payload.get("after")
            for project in await repo.list_project_twins():
                if project.repo_full_name == full_name:
                    project.health_status = "remote_changed"
                    if after and project.last_indexed_commit != after:
                        project.index_status = "stale"
                    await repo.save_project_twin(project)

        return {"event": event_name, "action": action, "installation_id": installation_id or None}

    async def list_installation_repos(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        installations = await get_repository().list_github_installations()
        repos: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for installation in installations:
                if installation.status != "active":
                    continue
                token = await self.create_installation_token(installation.installation_id)
                response = await client.get(
                    f"{GITHUB_API_BASE}/installation/repositories",
                    headers=self._installation_headers(token),
                )
                response.raise_for_status()
                for item in response.json().get("repositories", []):
                    repos.append(self._repo_to_dict(item, installation.installation_id))
        return repos

    async def create_draft_pull_request(
        self,
        installation_id: str,
        owner: str,
        repo_name: str,
        title: str,
        head_branch: str,
        base_branch: str,
        body: str = "",
    ) -> dict[str, Any]:
        self._require_configured()
        await self._require_active_installation(installation_id)
        token = await self.create_installation_token(installation_id)
        request_body = {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body,
            "draft": True,
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}/pulls",
                    headers=self._installation_headers(token),
                    json=request_body,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            response = exc.response
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(
                f"GitHub draft pull request creation failed "
                f"({response.status_code}): {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"GitHub draft pull request creation failed: {exc}") from exc

        data = response.json()
        return {
            "url": data.get("url") or "",
            "html_url": data.get("html_url") or "",
            "number": data.get("number"),
            "state": data.get("state") or "",
            "draft": bool(data.get("draft", True)),
        }

    async def create_installation_token(self, installation_id: str) -> str:
        self._require_configured()
        await self._require_active_installation(installation_id)
        token = self._app_jwt()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response.raise_for_status()
            return response.json()["token"]

    async def get_repo(self, installation_id: str, owner: str, repo_name: str) -> dict[str, Any]:
        token = await self.create_installation_token(installation_id)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}",
                headers=self._installation_headers(token),
            )
            response.raise_for_status()
            return self._repo_to_dict(response.json(), installation_id)

    def _app_jwt(self) -> str:
        try:
            import jwt
        except ImportError as exc:
            raise RuntimeError("PyJWT is required for GitHub App authentication") from exc

        now = int(time.time())
        return jwt.encode(
            {"iat": now - 60, "exp": now + 540, "iss": settings.github_app_id},
            self._private_key(),
            algorithm="RS256",
        )

    def _private_key(self) -> str:
        if settings.github_app_private_key:
            return settings.github_app_private_key.replace("\\n", "\n")
        if settings.github_app_private_key_path:
            return Path(settings.github_app_private_key_path).read_text(encoding="utf-8")
        return ""

    def _require_configured(self) -> None:
        if not settings.github_app_id:
            raise ValueError("GitHub App is not configured: missing GITHUB_APP_ID")
        try:
            private_key = self._private_key()
        except OSError as exc:
            raise ValueError(f"GitHub App private key could not be read: {exc}") from exc
        if not private_key:
            raise ValueError("GitHub App is not configured: missing private key")

    async def _require_active_installation(self, installation_id: str) -> GitHubInstallation:
        installation = await get_repository().get_github_installation(installation_id)
        if installation is None:
            raise ValueError(f"GitHub installation {installation_id} was not found")
        if installation.status != "active":
            raise ValueError(f"GitHub installation {installation_id} is not active")
        return installation

    def _installation_headers(self, token: str) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _repo_to_dict(self, item: dict[str, Any], installation_id: str) -> dict[str, Any]:
        return {
            "installation_id": str(installation_id),
            "owner": item.get("owner", {}).get("login") or "",
            "repo": item.get("name") or "",
            "repo_full_name": item.get("full_name") or "",
            "repo_url": item.get("html_url") or "",
            "clone_url": item.get("clone_url") or "",
            "default_branch": item.get("default_branch") or "main",
            "private": bool(item.get("private", False)),
            "description": item.get("description") or "",
        }
