from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.app.repository import InMemoryRepository, set_repository
from backend.app.services.golden_factory_harness import BUILTIN_HARNESS_SCHEMA_VERSION, BUILTIN_TEMPLATE_ID, GoldenFactoryHarnessService


@pytest.mark.asyncio
async def test_golden_factory_harness_service_exposes_v0_contract() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    service = GoldenFactoryHarnessService()

    harness = await service.get_harness(BUILTIN_TEMPLATE_ID)

    assert harness is not None
    metadata = harness["harness_metadata"]
    assert metadata["template_id"] == BUILTIN_TEMPLATE_ID
    assert metadata["schema_version"] == BUILTIN_HARNESS_SCHEMA_VERSION
    assert sum(metadata["scorecard_weights"].values()) == 100
    assert metadata["fixture_requirements"]["seed_sql_path"] == "supabase/seed.sql"
    assert metadata["fixture_requirements"]["stripe_fixtures_path"] == "fixtures/stripe-fixtures.json"
    assert "Free Tier user" in metadata["fixture_requirements"]["supabase_seed_requirements"]
    assert "Deterministic Stripe subscription deleted webhook payload" in metadata["fixture_requirements"]["stripe_webhook_payloads"]

    scenarios = harness["scenarios"]
    assert len(scenarios) == 3
    assert "playwright_checkout_mocked_e2e" not in {scenario["id"] for scenario in scenarios}

    for scenario in scenarios:
        assert scenario["lifecycle_status"] == "active"
        assert scenario["user_intent"]
        assert scenario["risk_level"] in {"medium", "high"}
        assert scenario["expected_touched_files_modules"]
        assert scenario["verification_commands"]
        assert scenario["graphify_checks"]
        assert scenario["success_criteria"]
        assert scenario["failure_modes"]
        assert sum(scenario["scorecard_weights"].values()) == 100
        expectations = scenario["review_packet_expectations"]
        assert expectations["wait_window_state"] == "awaiting_review"
        assert expectations["allowed_actions"]
        if scenario["risk_level"] == "high":
            assert expectations["human_in_the_loop_required"] is True


@pytest.mark.asyncio
async def test_golden_factory_harness_service_can_include_deferred_scenario() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    service = GoldenFactoryHarnessService()

    harness = await service.get_harness(BUILTIN_TEMPLATE_ID, include_deferred=True)

    assert harness is not None
    scenario_ids = {scenario["id"] for scenario in harness["scenarios"]}
    assert "playwright_checkout_mocked_e2e" in scenario_ids


@pytest.mark.asyncio
async def test_golden_factory_harness_api_returns_default_active_scenarios(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/templates/karkhana-golden-sveltekit-supabase-stripe/golden-factory-harness")
    assert response.status_code == 200
    data = response.json()["golden_factory_harness"]

    assert data["harness_metadata"]["template_id"] == BUILTIN_TEMPLATE_ID
    assert len(data["scenarios"]) == 3
    assert "playwright_checkout_mocked_e2e" not in {scenario["id"] for scenario in data["scenarios"]}


@pytest.mark.asyncio
async def test_golden_factory_harness_api_can_include_deferred_scenario(test_client: AsyncClient) -> None:
    response = await test_client.get(
        "/api/templates/karkhana-golden-sveltekit-supabase-stripe/golden-factory-harness",
        params={"include_deferred": "true"},
    )
    assert response.status_code == 200
    data = response.json()["golden_factory_harness"]

    assert len(data["scenarios"]) == 4
    assert "playwright_checkout_mocked_e2e" in {scenario["id"] for scenario in data["scenarios"]}


@pytest.mark.asyncio
async def test_golden_factory_harness_api_returns_404_for_unknown_templates(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/templates/unknown-template/golden-factory-harness")
    assert response.status_code == 404

