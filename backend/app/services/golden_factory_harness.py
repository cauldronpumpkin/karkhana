from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from backend.app.services.project_twin import to_jsonable
from backend.app.services.template_pack import BUILTIN_TEMPLATE_ID, TemplatePackService


BUILTIN_HARNESS_SCHEMA_VERSION = "v0"

HARNESS_SCORECARD_WEIGHTS = {
    "task_success": 25,
    "template_compliance": 15,
    "process_compliance": 15,
    "blast_radius_accuracy": 15,
    "repair_loop_behavior": 10,
    "human_review_usefulness": 10,
    "token_cost_and_time_to_review": 10,
}


@dataclass(slots=True)
class HarnessFixtureRequirements:
    seed_sql_path: str = "supabase/seed.sql"
    stripe_fixtures_path: str = "fixtures/stripe-fixtures.json"
    supabase_seed_requirements: list[str] = field(default_factory=lambda: [
        "Fixed UUIDs",
        "Deterministic users",
        "Free Tier user",
        "Pro Tier user with mocked stripe_customer_id",
        "Seeded projects",
    ])
    stripe_webhook_payloads: list[str] = field(default_factory=lambda: [
        "Deterministic Stripe subscription created webhook payload",
        "Deterministic Stripe subscription updated webhook payload",
        "Deterministic Stripe subscription deleted webhook payload",
    ])


@dataclass(slots=True)
class ReviewPacketExpectationContract:
    execution_trace: dict[str, Any] = field(default_factory=lambda: {
        "trace_id": "trace-placeholder",
        "span_ids": ["planner", "implementation", "review"],
    })
    changed_files: list[str] = field(default_factory=list)
    blast_radius: dict[str, Any] = field(default_factory=dict)
    safety_net_results: dict[str, Any] = field(default_factory=dict)
    wait_window_state: str = "awaiting_review"
    allowed_actions: list[str] = field(default_factory=lambda: ["request_changes", "approve"])
    token_cost_expectations: dict[str, Any] | None = None
    time_to_review_expectations: dict[str, Any] | None = None
    human_in_the_loop_required: bool = True


@dataclass(slots=True)
class GoldenFactoryHarnessScenario:
    id: str
    name: str
    lifecycle_status: str
    user_intent: str
    risk_level: str
    expected_touched_files_modules: list[str] = field(default_factory=list)
    expected_db_schema_changes: list[str] = field(default_factory=list)
    expected_stripe_changes: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    graphify_checks: list[str] = field(default_factory=list)
    review_packet_expectations: ReviewPacketExpectationContract = field(default_factory=ReviewPacketExpectationContract)
    success_criteria: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    scorecard_weights: dict[str, int] = field(default_factory=lambda: dict(HARNESS_SCORECARD_WEIGHTS))


@dataclass(slots=True)
class GoldenFactoryHarnessMetadata:
    template_id: str
    template_version: str
    schema_version: str = BUILTIN_HARNESS_SCHEMA_VERSION
    fixture_requirements: HarnessFixtureRequirements = field(default_factory=HarnessFixtureRequirements)
    scorecard_weights: dict[str, int] = field(default_factory=lambda: dict(HARNESS_SCORECARD_WEIGHTS))


@dataclass(slots=True)
class GoldenFactoryHarnessContract:
    harness_metadata: GoldenFactoryHarnessMetadata
    scenarios: list[GoldenFactoryHarnessScenario]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["harness_metadata"]["fixture_requirements"] = asdict(self.harness_metadata.fixture_requirements)
        payload["scenarios"] = [
            {
                **asdict(scenario),
                "review_packet_expectations": to_jsonable(scenario.review_packet_expectations),
            }
            for scenario in self.scenarios
        ]
        return payload


class GoldenFactoryHarnessService:
    def __init__(self, template_service: TemplatePackService | None = None) -> None:
        self._template_service = template_service or TemplatePackService()

    async def get_harness(self, template_id: str, *, include_deferred: bool = False) -> dict[str, Any] | None:
        if template_id != BUILTIN_TEMPLATE_ID:
            return None

        pack = await self._template_service.get_template_pack(template_id)
        if not pack:
            return None

        contract = GoldenFactoryHarnessContract(
            harness_metadata=GoldenFactoryHarnessMetadata(
                template_id=template_id,
                template_version=str(pack.get("version") or ""),
            ),
            scenarios=self._scenario_registry(include_deferred=include_deferred),
        )
        self._validate_contract(contract)
        return contract.to_dict()

    def _scenario_registry(self, *, include_deferred: bool) -> list[GoldenFactoryHarnessScenario]:
        scenarios = [
            GoldenFactoryHarnessScenario(
                id="tier_based_access_control",
                name="Tier Based Access Control",
                lifecycle_status="active",
                user_intent="Add tier-aware access control so Free and Pro users see the right capabilities.",
                risk_level="high",
                expected_touched_files_modules=[
                    "backend/app/services/authz.py",
                    "backend/app/services/template_pack.py",
                    "backend/app/routers/templates.py",
                    "supabase/migrations/*",
                ],
                expected_db_schema_changes=[
                    "Add or evolve entitlement fields for free vs pro tier access.",
                    "Adjust row-level security policies for tier-gated resources.",
                ],
                expected_stripe_changes=[],
                verification_commands=[
                    "python -m pytest backend/tests/test_golden_factory_harness.py",
                    "python -m pytest backend/tests/test_template_pack_api.py",
                    "graphify update .",
                ],
                graphify_checks=[
                    "Read graphify-out/GRAPH_REPORT.md before editing",
                    "Run graphify update . after contract changes",
                ],
                review_packet_expectations=ReviewPacketExpectationContract(
                    changed_files=[
                        "backend/app/services/authz.py",
                        "backend/app/routers/templates.py",
                        "supabase/migrations/*",
                    ],
                    blast_radius={
                        "modules": ["authz", "templates", "database"],
                        "db_schema": ["rls", "entitlements"],
                    },
                    safety_net_results={
                        "verification_commands": [
                            "python -m pytest backend/tests/test_golden_factory_harness.py",
                            "graphify update .",
                        ],
                        "graphify_required": True,
                    },
                    wait_window_state="awaiting_review",
                    allowed_actions=["request_changes", "approve"],
                    human_in_the_loop_required=True,
                ),
                success_criteria=[
                    "Free and Pro users resolve to different access scopes.",
                    "No unrelated template pack or worker queue mutation occurs.",
                ],
                failure_modes=[
                    "Tier checks bypassed for Free users.",
                    "RLS changes widen access unintentionally.",
                ],
            ),
            GoldenFactoryHarnessScenario(
                id="stripe_subscription_deleted_webhook",
                name="Stripe Subscription Deleted Webhook",
                lifecycle_status="active",
                user_intent="Handle a deleted Stripe subscription deterministically and keep billing state consistent.",
                risk_level="high",
                expected_touched_files_modules=[
                    "backend/app/services/stripe_webhooks.py",
                    "backend/app/routers/webhooks.py",
                    "fixtures/stripe-fixtures.json",
                    "supabase/seed.sql",
                ],
                expected_db_schema_changes=[
                    "Persist deterministic subscription status transitions.",
                    "Preserve customer linkage for mocked Stripe customer ids.",
                ],
                expected_stripe_changes=[
                    "Consume subscription.created payloads.",
                    "Consume subscription.updated payloads.",
                    "Consume subscription.deleted payloads.",
                ],
                verification_commands=[
                    "python -m pytest backend/tests/test_golden_factory_harness.py",
                    "python -m pytest backend/tests/test_template_pack_api.py",
                    "graphify update .",
                ],
                graphify_checks=[
                    "Read graphify-out/GRAPH_REPORT.md before editing",
                    "Run graphify update . after backend contract changes",
                ],
                review_packet_expectations=ReviewPacketExpectationContract(
                    changed_files=[
                        "backend/app/services/stripe_webhooks.py",
                        "fixtures/stripe-fixtures.json",
                        "supabase/seed.sql",
                    ],
                    blast_radius={
                        "modules": ["webhooks", "fixtures", "billing"],
                        "stripe_events": ["created", "updated", "deleted"],
                    },
                    safety_net_results={
                        "verification_commands": [
                            "python -m pytest backend/tests/test_golden_factory_harness.py",
                            "graphify update .",
                        ],
                        "graphify_required": True,
                    },
                    wait_window_state="awaiting_review",
                    allowed_actions=["request_changes", "approve"],
                    human_in_the_loop_required=True,
                ),
                success_criteria=[
                    "Subscription deletion does not desynchronize billing state.",
                    "Fixture payloads stay deterministic.",
                ],
                failure_modes=[
                    "Webhook state becomes non-deterministic.",
                    "Subscription deletion path drops customer linkage.",
                ],
            ),
            GoldenFactoryHarnessScenario(
                id="team_schema_rls_evolution",
                name="Team Schema and RLS Evolution",
                lifecycle_status="active",
                user_intent="Evolve the team schema and row-level security without breaking seeded project access.",
                risk_level="medium",
                expected_touched_files_modules=[
                    "supabase/migrations/*",
                    "backend/app/repository.py",
                    "backend/app/services/project_twin.py",
                    "backend/tests",
                ],
                expected_db_schema_changes=[
                    "Adjust team membership schema and access relationships.",
                    "Update row-level security rules for team-scoped data.",
                ],
                expected_stripe_changes=[],
                verification_commands=[
                    "python -m pytest backend/tests/test_golden_factory_harness.py",
                    "python -m pytest backend/tests/test_template_pack_api.py",
                    "graphify update .",
                ],
                graphify_checks=[
                    "Read graphify-out/GRAPH_REPORT.md before editing",
                    "Run graphify update . after schema changes",
                ],
                review_packet_expectations=ReviewPacketExpectationContract(
                    changed_files=[
                        "supabase/migrations/*",
                        "backend/app/repository.py",
                        "backend/app/services/project_twin.py",
                    ],
                    blast_radius={
                        "modules": ["repository", "project_twin", "database"],
                        "schema": ["team_members", "rls"],
                    },
                    safety_net_results={
                        "verification_commands": [
                            "python -m pytest backend/tests/test_golden_factory_harness.py",
                            "graphify update .",
                        ],
                        "graphify_required": True,
                    },
                    wait_window_state="awaiting_review",
                    allowed_actions=["request_changes", "approve"],
                    human_in_the_loop_required=True,
                ),
                success_criteria=[
                    "Seeded projects still resolve against team membership.",
                    "Access control remains deterministic for the harness.",
                ],
                failure_modes=[
                    "Team access changes leak across tenants.",
                    "Schema evolution breaks seeded fixtures.",
                ],
            ),
            GoldenFactoryHarnessScenario(
                id="playwright_checkout_mocked_e2e",
                name="Playwright Checkout Mocked E2E",
                lifecycle_status="do_later",
                user_intent="Exercise a mocked checkout flow with browser automation after the contract layer is ready.",
                risk_level="high",
                expected_touched_files_modules=[
                    "frontend/tests/e2e/checkout.spec.ts",
                    "playwright.config.ts",
                    "fixtures/stripe-fixtures.json",
                ],
                expected_db_schema_changes=[],
                expected_stripe_changes=[
                    "Mock checkout completion and subscription lifecycle payloads.",
                ],
                verification_commands=[
                    "pnpm test:e2e",
                    "graphify update .",
                ],
                graphify_checks=[
                    "Read graphify-out/GRAPH_REPORT.md before editing",
                    "Run graphify update . after adding E2E coverage",
                ],
                review_packet_expectations=ReviewPacketExpectationContract(
                    changed_files=[
                        "frontend/tests/e2e/checkout.spec.ts",
                        "playwright.config.ts",
                    ],
                    blast_radius={
                        "modules": ["frontend", "playwright", "fixtures"],
                    },
                    safety_net_results={
                        "verification_commands": [
                            "pnpm test:e2e",
                            "graphify update .",
                        ],
                        "graphify_required": True,
                    },
                    wait_window_state="awaiting_review",
                    allowed_actions=["request_changes", "approve"],
                    human_in_the_loop_required=True,
                ),
                success_criteria=[
                    "Browser flow can be exercised against mocked Stripe data.",
                    "Scenario remains deferred until the execution harness exists.",
                ],
                failure_modes=[
                    "E2E automation becomes part of the runnable v0 set too early.",
                    "Checkout mocks drift from the deterministic Stripe fixtures.",
                ],
            ),
        ]

        if include_deferred:
            return scenarios
        return [scenario for scenario in scenarios if scenario.lifecycle_status == "active"]

    def _validate_contract(self, contract: GoldenFactoryHarnessContract) -> None:
        scorecard_total = sum(contract.harness_metadata.scorecard_weights.values())
        if scorecard_total != 100:
            raise ValueError(f"Harness scorecard weights must sum to 100, got {scorecard_total}")

        active_scenarios = [scenario for scenario in contract.scenarios if scenario.lifecycle_status == "active"]
        for scenario in active_scenarios:
            if not scenario.verification_commands:
                raise ValueError(f"Active scenario '{scenario.id}' must define verification commands")
            if not scenario.graphify_checks:
                raise ValueError(f"Active scenario '{scenario.id}' must define Graphify checks")
            expectations = scenario.review_packet_expectations
            if scenario.risk_level == "high" and not expectations.human_in_the_loop_required:
                raise ValueError(f"High-risk scenario '{scenario.id}' must require human-in-the-loop review")
            if not expectations.allowed_actions:
                raise ValueError(f"Scenario '{scenario.id}' must define allowed review actions")

