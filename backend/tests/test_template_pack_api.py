import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_templates_api_returns_builtin_seed(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/templates")
    assert response.status_code == 200
    data = response.json()

    assert len(data["template_packs"]) >= 1
    pack = next(item for item in data["template_packs"] if item["template_id"] == "karkhana-golden-sveltekit-supabase-stripe")
    assert pack["manifest"]["schema_version"] == "v0"
    assert pack["status"] == "stable"
    assert pack["context_card_count"] == 3
    assert pack["token_profile"]["strategy"] == "curated"
    assert "graphify update ." in pack["verification_commands"]


@pytest.mark.asyncio
async def test_get_template_manifest_api(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/templates/karkhana-golden-sveltekit-supabase-stripe/manifest")
    assert response.status_code == 200
    data = response.json()

    assert data["manifest"]["id"] == "karkhana-golden-sveltekit-supabase-stripe"
    assert data["manifest"]["required_tools"] == ["node", "pnpm", "supabase", "stripe"]
    assert data["manifest"]["status"] == "stable"
    assert len(data["manifest"]["context_cards"]) == 3
    assert "AGENTS.md" in data["manifest"]["artifact_map"]
    assert data["manifest"]["review_metadata"]["guardrail_policy"] == "strict"


@pytest.mark.asyncio
async def test_get_template_context_cards_api(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/templates/karkhana-golden-sveltekit-supabase-stripe/context-cards")
    assert response.status_code == 200
    data = response.json()

    assert data["template_id"] == "karkhana-golden-sveltekit-supabase-stripe"
    assert data["context_card_count"] == 3
    assert data["token_profile"]["strategy"] == "curated"
    assert len(data["context_cards"]) == 3
    assert data["context_cards"][0]["referenced_files"]


@pytest.mark.asyncio
async def test_validate_template_api_reports_guardrail_failures(test_client: AsyncClient) -> None:
    response = await test_client.post(
        "/api/templates/karkhana-golden-sveltekit-supabase-stripe/validate",
        json={
            "changed_files": [".karkhana/worker.ts", "backend/tests/verification/harness.ts"],
            "mode": "normal",
            "verification_commands": ["pnpm test"],
            "graphify_updated": False,
            "completed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["valid"] is False
    assert data["guardrail_state"] == "fail"
    assert any(issue["code"] == "path_forbidden" for issue in data["issues"])
    assert any(issue["code"] == "missing_graphify_command" for issue in data["issues"])
