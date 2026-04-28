from __future__ import annotations

import pytest

from backend.app.repository import (
    AUTONOMY_AUTONOMOUS_DEVELOPMENT,
    AUTONOMY_FULL_AUTOPILOT,
    AUTONOMY_LEVELS,
    AUTONOMY_SUGGEST_ONLY,
    Idea,
    InMemoryRepository,
    ProjectTwin,
    TemplatePack,
    set_repository,
    utcnow,
)
from backend.app.services.autonomy import (
    AUTONOMY_DESCRIPTIONS,
    GuardrailViolation,
    can_auto_advance_phase,
    can_auto_repair,
    can_bypass_repair_limits,
    can_enqueue_work,
    check_guardrails,
    get_autonomy_level,
    validate_autonomy_level,
)
from backend.app.services.factory_orchestrator import FactoryOrchestratorService
from backend.app.services.factory_run import FactoryRunService


async def _seed_project_and_template(repo: InMemoryRepository):
    idea = Idea(title="Autonomy Test", slug="autonomy-test", description="test")
    await repo.create_idea(idea)

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="inst-1",
        owner="acme",
        repo="app",
        repo_full_name="acme/app",
        repo_url="https://github.com/acme/app",
        clone_url="https://github.com/acme/app.git",
        default_branch="main",
    )
    await repo.save_project_twin(project)

    template = TemplatePack(
        template_id="multi-phase-v1",
        version="1.0.0",
        channel="stable",
        display_name="Multi-Phase",
        description="",
        phases=[
            {"key": "scaffold", "label": "Scaffold"},
            {"key": "backend", "label": "Backend"},
        ],
    )
    await repo.save_template_pack(template)

    return idea, project, template


@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


class TestAutonomyConstants:
    def test_valid_levels(self):
        assert AUTONOMY_SUGGEST_ONLY in AUTONOMY_LEVELS
        assert AUTONOMY_AUTONOMOUS_DEVELOPMENT in AUTONOMY_LEVELS
        assert AUTONOMY_FULL_AUTOPILOT in AUTONOMY_LEVELS
        assert len(AUTONOMY_LEVELS) == 3

    def test_level_values(self):
        assert AUTONOMY_SUGGEST_ONLY == "suggest_only"
        assert AUTONOMY_AUTONOMOUS_DEVELOPMENT == "autonomous_development"
        assert AUTONOMY_FULL_AUTOPILOT == "full_autopilot"


class TestValidateAutonomyLevel:
    def test_valid_levels(self):
        assert validate_autonomy_level("suggest_only") == "suggest_only"
        assert validate_autonomy_level("autonomous_development") == "autonomous_development"
        assert validate_autonomy_level("full_autopilot") == "full_autopilot"

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="Invalid autonomy_level"):
            validate_autonomy_level("invalid")

    def test_invalid_level_message_contains_valid_options(self):
        with pytest.raises(ValueError, match="autonomous_development.*full_autopilot.*suggest_only"):
            validate_autonomy_level("nope")


class TestGetAutonomyLevel:
    def test_returns_configured_level(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(
            idea_id="i1",
            template_id="t1",
            config={"autonomy_level": AUTONOMY_SUGGEST_ONLY},
        )
        assert get_autonomy_level(run) == AUTONOMY_SUGGEST_ONLY

    def test_defaults_to_autonomous_development(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={})
        assert get_autonomy_level(run) == AUTONOMY_AUTONOMOUS_DEVELOPMENT

    def test_defaults_when_no_config(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1")
        assert get_autonomy_level(run) == AUTONOMY_AUTONOMOUS_DEVELOPMENT


class TestCanEnqueueWork:
    def test_suggest_only_cannot(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_SUGGEST_ONLY})
        assert can_enqueue_work(run) is False

    def test_autonomous_development_can(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_AUTONOMOUS_DEVELOPMENT})
        assert can_enqueue_work(run) is True

    def test_full_autopilot_can(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        assert can_enqueue_work(run) is True


class TestCanAutoAdvancePhase:
    def test_suggest_only_cannot(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_SUGGEST_ONLY})
        assert can_auto_advance_phase(run) is False

    def test_autonomous_development_can(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_AUTONOMOUS_DEVELOPMENT})
        assert can_auto_advance_phase(run) is True

    def test_full_autopilot_can(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        assert can_auto_advance_phase(run) is True


class TestCanAutoRepair:
    def test_suggest_only_cannot(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_SUGGEST_ONLY})
        assert can_auto_repair(run) is False

    def test_autonomous_development_can(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_AUTONOMOUS_DEVELOPMENT})
        assert can_auto_repair(run) is True

    def test_full_autopilot_can(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        assert can_auto_repair(run) is True


class TestCanBypassRepairLimits:
    def test_suggest_only_cannot(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_SUGGEST_ONLY})
        assert can_bypass_repair_limits(run) is False

    def test_autonomous_development_cannot(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_AUTONOMOUS_DEVELOPMENT})
        assert can_bypass_repair_limits(run) is False

    def test_full_autopilot_can(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        assert can_bypass_repair_limits(run) is True


class TestCheckGuardrails:
    def test_deploy_to_production_blocked(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        with pytest.raises(GuardrailViolation, match="deploy_to_production"):
            check_guardrails(run, "deploy_to_production")

    def test_add_paid_service_blocked(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        with pytest.raises(GuardrailViolation, match="add_paid_service"):
            check_guardrails(run, "add_paid_service")

    def test_commit_secrets_blocked(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        with pytest.raises(GuardrailViolation, match="commit_secrets"):
            check_guardrails(run, "commit_secrets")

    def test_destructive_db_change_blocked(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        with pytest.raises(GuardrailViolation, match="destructive_db_change"):
            check_guardrails(run, "destructive_db_change")

    def test_guardrails_block_even_suggest_only(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_SUGGEST_ONLY})
        with pytest.raises(GuardrailViolation):
            check_guardrails(run, "deploy_to_production")

    def test_allowed_operation_passes(self):
        from backend.app.repository import FactoryRun
        run = FactoryRun(idea_id="i1", template_id="t1", config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT})
        check_guardrails(run, "run_tests")
        check_guardrails(run, "build_frontend")
        check_guardrails(run, "create_branch")


class TestAutonomyDescriptions:
    def test_all_levels_have_descriptions(self):
        for level in AUTONOMY_LEVELS:
            assert level in AUTONOMY_DESCRIPTIONS
            desc = AUTONOMY_DESCRIPTIONS[level]
            assert "label" in desc
            assert "short" in desc
            assert "long" in desc
            assert "behaviors" in desc

    def test_behavior_matrix(self):
        assert AUTONOMY_DESCRIPTIONS[AUTONOMY_SUGGEST_ONLY]["behaviors"] == {
            "enqueue_work": False,
            "auto_advance": False,
            "auto_repair": False,
            "bypass_limits": False,
        }
        assert AUTONOMY_DESCRIPTIONS[AUTONOMY_AUTONOMOUS_DEVELOPMENT]["behaviors"] == {
            "enqueue_work": True,
            "auto_advance": True,
            "auto_repair": True,
            "bypass_limits": False,
        }
        assert AUTONOMY_DESCRIPTIONS[AUTONOMY_FULL_AUTOPILOT]["behaviors"] == {
            "enqueue_work": True,
            "auto_advance": True,
            "auto_repair": True,
            "bypass_limits": True,
        }


class TestSuggestOnlyIntegration:
    @pytest.mark.asyncio
    async def test_suggest_only_creates_run_without_work_item(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()
        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_SUGGEST_ONLY,
        )

        assert result["factory_run"]["config"]["autonomy_level"] == AUTONOMY_SUGGEST_ONLY
        assert result["work_item"] is None
        assert result["first_batch"] is not None
        assert result["factory_run"]["status"] == "running"
        assert len(result["phases"]) == 2

    @pytest.mark.asyncio
    async def test_suggest_only_does_not_advance_phase_on_completion(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()

        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_AUTONOMOUS_DEVELOPMENT,
        )
        run_id = result["factory_run"]["id"]
        work_item_id = result["work_item"]["id"]

        run = await repo.get_factory_run(run_id)
        run.config["autonomy_level"] = AUTONOMY_SUGGEST_ONLY
        await repo.save_factory_run(run)

        work_item = await repo.get_work_item(work_item_id)
        work_item.status = "completed"
        work_item.result = {"summary": "Done", "tests_passed": True}
        await repo.save_work_item(work_item)

        orchestrator = FactoryOrchestratorService()
        orch_result = await orchestrator.on_task_completed(work_item_id)

        assert orch_result is not None
        assert orch_result["action"] == "awaiting_approval"
        assert "backend" in orch_result["reason"]

        phases = await repo.list_factory_phases(run_id)
        assert phases[0].status == "completed"
        assert phases[1].status == "pending"

    @pytest.mark.asyncio
    async def test_suggest_only_does_not_auto_repair_on_failure(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()

        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_AUTONOMOUS_DEVELOPMENT,
        )
        run_id = result["factory_run"]["id"]
        work_item_id = result["work_item"]["id"]
        batch_id = result["first_batch"]["id"]

        run = await repo.get_factory_run(run_id)
        run.config["autonomy_level"] = AUTONOMY_SUGGEST_ONLY
        await repo.save_factory_run(run)

        work_item = await repo.get_work_item(work_item_id)
        work_item.status = "failed_terminal"
        work_item.error = "Build crashed"
        await repo.save_work_item(work_item)

        orchestrator = FactoryOrchestratorService()
        orch_result = await orchestrator.on_task_failed(work_item_id)

        assert orch_result is not None
        assert orch_result["action"] == "run_failed"

        batch = await repo.get_factory_batch(batch_id)
        assert batch.status == "failed"

        repairs = await repo.list_repair_tasks(run_id)
        assert len(repairs) == 0


class TestAutonomousDevelopmentIntegration:
    @pytest.mark.asyncio
    async def test_autonomous_development_creates_work_item(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()
        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_AUTONOMOUS_DEVELOPMENT,
        )

        assert result["work_item"] is not None
        assert result["work_item"]["status"] == "queued"
        assert result["factory_run"]["config"]["autonomy_level"] == AUTONOMY_AUTONOMOUS_DEVELOPMENT

    @pytest.mark.asyncio
    async def test_autonomous_development_auto_advances_phases(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()
        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_AUTONOMOUS_DEVELOPMENT,
        )
        run_id = result["factory_run"]["id"]
        work_item_id = result["work_item"]["id"]

        work_item = await repo.get_work_item(work_item_id)
        work_item.status = "completed"
        work_item.result = {"summary": "Scaffold done", "tests_passed": True}
        await repo.save_work_item(work_item)

        orchestrator = FactoryOrchestratorService()
        orch_result = await orchestrator.on_task_completed(work_item_id)

        assert orch_result["action"] == "phase_advanced"
        assert orch_result["next_phase"] == "backend"

    @pytest.mark.asyncio
    async def test_autonomous_development_auto_repairs(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()
        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_AUTONOMOUS_DEVELOPMENT,
        )
        run_id = result["factory_run"]["id"]
        work_item_id = result["work_item"]["id"]

        work_item = await repo.get_work_item(work_item_id)
        work_item.status = "failed_terminal"
        work_item.error = "Build crashed"
        await repo.save_work_item(work_item)

        orchestrator = FactoryOrchestratorService()
        orch_result = await orchestrator.on_task_failed(work_item_id)

        assert orch_result is not None
        assert orch_result["action"] == "repair_created"


class TestFullAutopilotIntegration:
    @pytest.mark.asyncio
    async def test_full_autopilot_creates_work_item(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()
        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_FULL_AUTOPILOT,
        )

        assert result["work_item"] is not None
        assert result["factory_run"]["config"]["autonomy_level"] == AUTONOMY_FULL_AUTOPILOT

    @pytest.mark.asyncio
    async def test_full_autopilot_auto_advances_all_phases(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()
        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_FULL_AUTOPILOT,
        )
        run_id = result["factory_run"]["id"]

        orchestrator = FactoryOrchestratorService()

        for i, expected_action in enumerate(["phase_advanced", "run_completed"]):
            phases = await repo.list_factory_phases(run_id)
            running_phase = next((p for p in phases if p.status == "running"), None)
            assert running_phase is not None

            batches = await repo.list_factory_batches(running_phase.id)
            work_item_id = batches[0].work_item_id

            work_item = await repo.get_work_item(work_item_id)
            work_item.status = "completed"
            work_item.result = {"summary": f"Phase {i + 1}", "tests_passed": True}
            await repo.save_work_item(work_item)

            orch_result = await orchestrator.on_task_completed(work_item_id)
            assert orch_result["action"] == expected_action

    @pytest.mark.asyncio
    async def test_full_autopilot_guardrails_still_block(self, repo):
        from backend.app.repository import FactoryRun
        run = FactoryRun(
            idea_id="i1",
            template_id="t1",
            config={"autonomy_level": AUTONOMY_FULL_AUTOPILOT},
        )
        with pytest.raises(GuardrailViolation):
            check_guardrails(run, "deploy_to_production")
        with pytest.raises(GuardrailViolation):
            check_guardrails(run, "add_paid_service")
        with pytest.raises(GuardrailViolation):
            check_guardrails(run, "commit_secrets")
        with pytest.raises(GuardrailViolation):
            check_guardrails(run, "destructive_db_change")

    @pytest.mark.asyncio
    async def test_full_autopilot_worker_contract_includes_guardrails(self, repo):
        _, project, template = await _seed_project_and_template(repo)
        svc = FactoryRunService()
        result = await svc.create_factory_run(
            project_id=project.id,
            template_id=template.template_id,
            autonomy_level=AUTONOMY_FULL_AUTOPILOT,
        )

        work_item = result["work_item"]
        payload = work_item["payload"]
        assert payload["autonomy_level"] == AUTONOMY_FULL_AUTOPILOT
        assert len(payload["guardrails"]) == 4
        guardrail_texts = " ".join(payload["guardrails"])
        assert "production" in guardrail_texts
        assert "paid" in guardrail_texts
        assert "secrets" in guardrail_texts
        assert "destructive" in guardrail_texts


# ── Engine capability validation tests ──

class TestValidateEngineForAutonomyLevel:
    def test_opencode_server_valid_for_all(self):
        from backend.app.services.autonomy import validate_engine_for_autonomy_level
        validate_engine_for_autonomy_level("opencode-server", "suggest_only")
        validate_engine_for_autonomy_level("opencode-server", "autonomous_development")
        validate_engine_for_autonomy_level("opencode-server", "full_autopilot")

    def test_limited_engines_rejected_for_high_autonomy(self):
        from backend.app.services.autonomy import validate_engine_for_autonomy_level
        for engine in ("opencode", "openclaude", "codex"):
            with pytest.raises(ValueError, match="limited fallback"):
                validate_engine_for_autonomy_level(engine, "autonomous_development")
            with pytest.raises(ValueError, match="limited fallback"):
                validate_engine_for_autonomy_level(engine, "full_autopilot")

    def test_limited_engines_allowed_for_suggest_only(self):
        from backend.app.services.autonomy import validate_engine_for_autonomy_level
        for engine in ("opencode", "openclaude", "codex"):
            validate_engine_for_autonomy_level(engine, "suggest_only")

    def test_error_message_includes_capabilities(self):
        from backend.app.services.autonomy import validate_engine_for_autonomy_level
        with pytest.raises(ValueError, match="permission_guard|circuit_breaker|litellm_proxy"):
            validate_engine_for_autonomy_level("openclaude", "autonomous_development")


class TestValidateWorkerCapabilitiesForAutonomy:
    def test_full_capabilities_pass(self):
        from backend.app.services.autonomy import (
            OPENCODE_SERVER_REQUIRED_CAPABILITIES,
            validate_worker_capabilities_for_autonomy,
        )
        caps = list(OPENCODE_SERVER_REQUIRED_CAPABILITIES)
        assert validate_worker_capabilities_for_autonomy(caps, "autonomous_development") == []
        assert validate_worker_capabilities_for_autonomy(caps, "full_autopilot") == []

    def test_partial_capabilities_return_missing(self):
        from backend.app.services.autonomy import validate_worker_capabilities_for_autonomy
        caps = ["repo_index", "agent_branch_work"]
        missing = validate_worker_capabilities_for_autonomy(caps, "autonomous_development")
        assert "permission_guard" in missing
        assert "circuit_breaker" in missing
        assert "litellm_proxy" in missing
        assert "diff_api" in missing
        assert "verification_runner" in missing
        assert "graphify_update" in missing

    def test_suggest_only_skips_validation(self):
        from backend.app.services.autonomy import validate_worker_capabilities_for_autonomy
        assert validate_worker_capabilities_for_autonomy(["repo_index"], "suggest_only") == []

    def test_empty_capabilities_fail_high_autonomy(self):
        from backend.app.services.autonomy import validate_worker_capabilities_for_autonomy
        missing = validate_worker_capabilities_for_autonomy([], "autonomous_development")
        assert len(missing) == 6


class TestHighAutonomyConstants:
    def test_high_autonomy_levels(self):
        from backend.app.services.autonomy import HIGH_AUTONOMY_LEVELS
        assert "autonomous_development" in HIGH_AUTONOMY_LEVELS
        assert "full_autopilot" in HIGH_AUTONOMY_LEVELS
        assert "suggest_only" not in HIGH_AUTONOMY_LEVELS

    def test_limited_engines(self):
        from backend.app.services.autonomy import LIMITED_ENGINES
        assert "opencode" in LIMITED_ENGINES
        assert "openclaude" in LIMITED_ENGINES
        assert "codex" in LIMITED_ENGINES
        assert "opencode-server" not in LIMITED_ENGINES
