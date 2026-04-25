from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from backend.app.services.github_app import GitHubAppService

router = APIRouter(prefix="/api/github", tags=["github"])

_service: GitHubAppService | None = None


def get_service() -> GitHubAppService:
    global _service
    if _service is None:
        _service = GitHubAppService()
    return _service


@router.post("/app/webhook")
async def github_app_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str | None = Header(default=None),
):
    body = await request.body()
    service = get_service()
    if not service.verify_webhook_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")
    payload = await request.json()
    return await service.handle_webhook(x_github_event, payload)


@router.get("/installations/repos")
async def list_installation_repos():
    service = get_service()
    try:
        return {
            "configured": service.is_configured(),
            "repos": await service.list_installation_repos(),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
