from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.app.models.expert_council import (
    COUNCIL_DECISION_BLOCKED,
    COUNCIL_DECISION_NEEDS_CHANGES,
    COUNCIL_DECISION_READY,
    EXPERT_AUTHORITY_ADVISORY,
    EXPERT_AUTHORITY_HARD_GATE,
    EXPERT_DECISION_APPROVED,
    EXPERT_DECISION_APPROVED_WITH_NOTES,
    EXPERT_DECISION_BLOCKED,
    EXPERT_DECISION_REQUESTS_CHANGES,
    ROLE_ARCHITECTURE,
    ROLE_PRIVACY,
    ROLE_PRODUCT_UX,
    ROLE_QA,
    ROLE_SECURITY,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    ArtifactPatchProposal,
    CouncilSummary,
    ExpertApproval,
    ExpertConflict,
    ExpertDecision,
    ExpertFinding,
    ExpertRoleManifest,
    ExpertTrigger,
)
from backend.app.services.expert_council import (
    DEFAULT_ROLE_MANIFESTS,
    ExpertCouncilService,
    derive_council_summary,
    detect_conflicts,
    evaluate_triggers,
    generate_deterministic_review,
)
from backend.app.repository import (
    CodeIndexArtifact,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    GitHubInstallation,
    Idea,
    InMemoryRepository,
    LocalWorker,
    ProjectTwin,
    RepairTask,
    TemplateArtifact,
    TemplatePack,
    VerificationRun,
    WorkItem,
    utcnow,
)


class TestExpertCouncilSchemas:
    def test_expert_trigger_round_trip(self):
        t = ExpertTrigger(trigger_type="test", description="desc", matched=True, evidence_refs=["a"], weight=2.0)
        d = t.to_dict()
        restored = ExpertTrigger.from_dict(d)
        assert restored.trigger_type == "test"
        assert restored.matched is True
        assert restored.evidence_refs == ["a"]

    def test_expert_finding_round_trip(self):
        f = ExpertFinding(severity=SEVERITY_HIGH, summary="test", category="cat", blocking=True, file_path="x.py")
        d = f.to_dict()
        restored = ExpertFinding.from_dict(d)
        assert restored.severity == SEVERITY_HIGH
        assert restored.blocking is True
        assert restored.file_path == "x.py"

    def test_expert_approval_round_trip(self):
        a = ExpertApproval(scope="scope", description="desc", confidence=0.9)
        restored = ExpertApproval.from_dict(a.to_dict())
        assert restored.confidence == 0.9

    def test_artifact_patch_proposal_round_trip(self):
        p = ArtifactPatchProposal(artifact_key="AGENTS.md", patch_description="test", auto_apply=False)
        restored = ArtifactPatchProposal.from_dict(p.to_dict())
        assert restored.artifact_key == "AGENTS.md"
        assert restored.auto_apply is False

    def test_expert_conflict_round_trip(self):
        c = ExpertConflict(role_a="security", role_b="qa", topic="test", description="desc")
        restored = ExpertConflict.from_dict(c.to_dict())
        assert restored.role_a == "security"

    def test_expert_role_manifest_round_trip(self):
        m = ExpertRoleManifest(
            role=ROLE_SECURITY,
            display_name="Security",
            authority=EXPERT_AUTHORITY_HARD_GATE,
            description="desc",
            triggers=[ExpertTrigger(trigger_type="t", description="d")],
        )
        d = m.to_dict()
        restored = ExpertRoleManifest.from_dict(d)
        assert restored.role == ROLE_SECURITY
        assert len(restored.triggers) == 1

    def test_expert_decision_round_trip(self):
        dec = ExpertDecision(
            role=ROLE_QA,
            display_name="QA",
            authority=EXPERT_AUTHORITY_HARD_GATE,
            decision=EXPERT_DECISION_BLOCKED,
            confidence=0.7,
            findings=[ExpertFinding(severity=SEVERITY_CRITICAL, summary="test", category="cat", blocking=True)],
            approvals=[ExpertApproval(scope="v", description="d")],
        )
        d = dec.to_dict()
        restored = ExpertDecision.from_dict(d)
        assert restored.role == ROLE_QA
        assert len(restored.findings) == 1
        assert len(restored.approvals) == 1

    def test_council_summary_round_trip(self):
        s = CouncilSummary(
            overall_decision=COUNCIL_DECISION_BLOCKED,
            highest_severity=SEVERITY_CRITICAL,
            unresolved_blockers_count=2,
            active_roles_count=3,
            conflicts=[ExpertConflict(role_a="a", role_b="b", topic="t", description="d")],
        )
        d = s.to_dict()
        restored = CouncilSummary.from_dict(d)
        assert restored.overall_decision == COUNCIL_DECISION_BLOCKED
        assert restored.unresolved_blockers_count == 2
        assert len(restored.conflicts) == 1


class TestDefaultRoleManifests:
    def test_all_five_roles_present(self):
        assert set(DEFAULT_ROLE_MANIFESTS.keys()) == {ROLE_SECURITY, ROLE_ARCHITECTURE, ROLE_PRIVACY, ROLE_QA, ROLE_PRODUCT_UX}

    def test_hard_gate_roles(self):
        for role in (ROLE_SECURITY, ROLE_ARCHITECTURE, ROLE_PRIVACY, ROLE_QA):
            assert DEFAULT_ROLE_MANIFESTS[role].authority == EXPERT_AUTHORITY_HARD_GATE

    def test_advisory_role(self):
        assert DEFAULT_ROLE_MANIFESTS[ROLE_PRODUCT_UX].authority == EXPERT_AUTHORITY_ADVISORY

    def test_all_have_triggers(self):
        for manifest in DEFAULT_ROLE_MANIFESTS.values():
            assert len(manifest.triggers) > 0

    def test_anti_bloat_limits(self):
        for manifest in DEFAULT_ROLE_MANIFESTS.values():
            assert manifest.max_blockers <= 3
            assert manifest.max_nonblocking_findings <= 5


class TestTriggerEvaluation:
    def _base_context(self):
        return {
            "changed_files": ["backend/app/main.py"],
            "safety_net": {"tests_passed": True, "graphify_status": "updated", "error_count": 0},
            "blast_radius": {"impact_score": "low", "total_files_changed": 1, "impacted_modules": []},
            "decision_gates": {"verification_expectations": [], "graphify_expectations": {}},
        }

    def test_no_triggers_on_clean_run(self):
        ctx = self._base_context()
        results = evaluate_triggers(**ctx)
        total_matched = sum(len(v) for v in results.values())
        assert total_matched == 0

    def test_security_sensitive_path(self):
        ctx = self._base_context()
        ctx["changed_files"] = ["backend/app/auth/login.py", "backend/app/auth/session.py"]
        results = evaluate_triggers(**ctx)
        assert len(results[ROLE_SECURITY]) >= 1

    def test_secret_exposure(self):
        ctx = self._base_context()
        ctx["changed_files"] = [".env", "config/credentials.json"]
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "secret_exposure_indicator" for t in results[ROLE_SECURITY])

    def test_dependency_change(self):
        ctx = self._base_context()
        ctx["changed_files"] = ["package.json", "requirements.txt"]
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "unsafe_dependency_change" for t in results[ROLE_SECURITY])

    def test_test_failure_triggers_qa(self):
        ctx = self._base_context()
        ctx["safety_net"] = {"tests_passed": False, "error_count": 3, "graphify_status": "updated"}
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "test_failure" for t in results[ROLE_QA])

    def test_graphify_unhealthy(self):
        ctx = self._base_context()
        ctx["safety_net"] = {"tests_passed": True, "graphify_status": "pending", "error_count": 0}
        ctx["decision_gates"] = {"graphify_expectations": {"expected": True}}
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "graphify_status_unhealthy" for t in results[ROLE_QA])

    def test_missing_verification(self):
        ctx = self._base_context()
        ctx["decision_gates"] = {
            "verification_expectations": ["pytest backend/tests"],
            "graphify_expectations": {},
        }
        ctx["safety_net"] = {"tests_passed": True, "graphify_status": "updated", "error_count": 0, "verification_commands": []}
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "missing_verification_evidence" for t in results[ROLE_QA])

    def test_high_blast_radius(self):
        ctx = self._base_context()
        ctx["blast_radius"] = {"impact_score": "high", "total_files_changed": 15, "impacted_modules": []}
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "high_blast_radius" for t in results[ROLE_ARCHITECTURE])

    def test_migration_no_rollback(self):
        ctx = self._base_context()
        ctx["changed_files"] = ["backend/migrations/001_add_users.py"]
        results = evaluate_triggers(**ctx)
        arch_triggers = results[ROLE_ARCHITECTURE]
        assert any(t.trigger_type == "migration_like_change" for t in arch_triggers)
        assert any(t.trigger_type == "missing_rollback" for t in arch_triggers)

    def test_customer_data_privacy(self):
        ctx = self._base_context()
        ctx["changed_files"] = ["backend/app/models/customer.py", "backend/app/billing/stripe.py"]
        results = evaluate_triggers(**ctx)
        assert len(results[ROLE_PRIVACY]) >= 1

    def test_customer_facing_ui(self):
        ctx = self._base_context()
        ctx["changed_files"] = ["frontend/src/lib/components/Dashboard.svelte"]
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "customer_facing_ui" for t in results[ROLE_PRODUCT_UX])

    def test_billing_stripe(self):
        ctx = self._base_context()
        ctx["changed_files"] = ["backend/app/billing/stripe_webhook.py"]
        results = evaluate_triggers(**ctx)
        assert any(t.trigger_type == "billing_stripe_change" for t in results[ROLE_PRODUCT_UX])


class TestDeterministicReviewGeneration:
    def _base_context(self):
        return {
            "safety_net": {"tests_passed": True, "graphify_status": "updated", "error_count": 0, "verification_commands": ["pytest"]},
            "blast_radius": {"impact_score": "low", "total_files_changed": 1, "impacted_modules": []},
            "changed_files": ["backend/app/main.py"],
            "decision_gates": {"verification_expectations": ["pytest"], "graphify_expectations": {}},
        }

    def test_inactive_when_no_triggers(self):
        ctx = self._base_context()
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_SECURITY]
        decision = generate_deterministic_review(ROLE_SECURITY, manifest, [], **ctx)
        assert decision.activated is False
        assert decision.decision == EXPERT_DECISION_APPROVED

    def test_qa_blocks_on_test_failure(self):
        ctx = self._base_context()
        ctx["safety_net"] = {"tests_passed": False, "error_count": 2, "graphify_status": "updated", "verification_commands": ["pytest"]}
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_QA]
        trigger = ExpertTrigger(trigger_type="test_failure", description="Tests failed", matched=True, evidence_refs=["errors:2"])
        decision = generate_deterministic_review(ROLE_QA, manifest, [trigger], **ctx)
        assert decision.decision == EXPERT_DECISION_BLOCKED
        assert any(f.blocking for f in decision.findings)

    def test_security_blocks_on_secret_exposure(self):
        ctx = self._base_context()
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_SECURITY]
        trigger = ExpertTrigger(trigger_type="secret_exposure_indicator", description="Secret", matched=True, evidence_refs=[".env"])
        decision = generate_deterministic_review(ROLE_SECURITY, manifest, [trigger], **ctx)
        assert decision.decision == EXPERT_DECISION_BLOCKED
        assert any(f.severity == SEVERITY_CRITICAL for f in decision.findings)

    def test_architecture_blocks_on_high_blast_no_rollback(self):
        ctx = self._base_context()
        ctx["blast_radius"] = {"impact_score": "high", "total_files_changed": 15, "impacted_modules": []}
        ctx["changed_files"] = ["backend/migrations/001_add_users.py"]
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_ARCHITECTURE]
        triggers = [
            ExpertTrigger(trigger_type="high_blast_radius", description="High blast", matched=True),
            ExpertTrigger(trigger_type="migration_like_change", description="Migration", matched=True),
            ExpertTrigger(trigger_type="missing_rollback", description="No rollback", matched=True),
        ]
        decision = generate_deterministic_review(ROLE_ARCHITECTURE, manifest, triggers, **ctx)
        assert decision.decision == EXPERT_DECISION_BLOCKED

    def test_product_ux_cannot_hard_block(self):
        ctx = self._base_context()
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_PRODUCT_UX]
        trigger = ExpertTrigger(trigger_type="customer_facing_ui", description="UI", matched=True)
        decision = generate_deterministic_review(ROLE_PRODUCT_UX, manifest, [trigger], **ctx)
        assert decision.decision != EXPERT_DECISION_BLOCKED

    def test_product_ux_critical_block_allowed(self):
        ctx = self._base_context()
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_PRODUCT_UX]
        trigger = ExpertTrigger(trigger_type="billing_stripe_change", description="Billing", matched=True)
        decision = generate_deterministic_review(ROLE_PRODUCT_UX, manifest, [trigger], **ctx)
        assert decision.decision in (
            EXPERT_DECISION_APPROVED_WITH_NOTES,
            EXPERT_DECISION_REQUESTS_CHANGES,
            EXPERT_DECISION_APPROVED,
        )


class TestAntiBloatRules:
    def test_max_blockers_enforced(self):
        findings = [
            ExpertFinding(severity=SEVERITY_HIGH, summary=f"Blocker {i}", category="cat", blocking=True, evidence_ref=f"ref_{i}")
            for i in range(10)
        ]
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_SECURITY]
        result = []
        from backend.app.services.expert_council import _enforce_anti_bloat
        capped = _enforce_anti_bloat(findings, manifest)
        blockers = [f for f in capped if f.blocking]
        assert len(blockers) <= manifest.max_blockers

    def test_max_nonblocking_enforced(self):
        findings = [
            ExpertFinding(severity=SEVERITY_LOW, summary=f"Note {i}", category="cat", blocking=False)
            for i in range(10)
        ]
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_SECURITY]
        from backend.app.services.expert_council import _enforce_anti_bloat
        capped = _enforce_anti_bloat(findings, manifest)
        assert len(capped) <= manifest.max_nonblocking_findings

    def test_low_severity_cannot_block(self):
        findings = [
            ExpertFinding(severity=SEVERITY_LOW, summary="Low", category="cat", blocking=True, evidence_ref="ref"),
        ]
        manifest = DEFAULT_ROLE_MANIFESTS[ROLE_SECURITY]
        from backend.app.services.expert_council import _enforce_anti_bloat
        capped = _enforce_anti_bloat(findings, manifest)
        assert all(not f.blocking for f in capped)


class TestCouncilSummary:
    def test_ready_when_all_approve(self):
        decisions = [
            ExpertDecision(role=ROLE_SECURITY, display_name="Sec", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_APPROVED, confidence=1.0, activated=True),
            ExpertDecision(role=ROLE_QA, display_name="QA", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_APPROVED, confidence=1.0, activated=True),
        ]
        summary = derive_council_summary(decisions)
        assert summary.overall_decision == COUNCIL_DECISION_READY
        assert summary.unresolved_blockers_count == 0

    def test_blocked_when_any_blocks(self):
        decisions = [
            ExpertDecision(role=ROLE_SECURITY, display_name="Sec", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_APPROVED, confidence=1.0, activated=True),
            ExpertDecision(role=ROLE_QA, display_name="QA", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_BLOCKED, confidence=0.5, activated=True,
                           findings=[ExpertFinding(severity=SEVERITY_CRITICAL, summary="Tests failed", category="test", blocking=True)]),
        ]
        summary = derive_council_summary(decisions)
        assert summary.overall_decision == COUNCIL_DECISION_BLOCKED
        assert summary.unresolved_blockers_count == 1

    def test_needs_changes_when_requested(self):
        decisions = [
            ExpertDecision(role=ROLE_ARCHITECTURE, display_name="Arch", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_REQUESTS_CHANGES, confidence=0.7, activated=True,
                           findings=[ExpertFinding(severity=SEVERITY_HIGH, summary="Refactor needed", category="arch", blocking=False)]),
        ]
        summary = derive_council_summary(decisions)
        assert summary.overall_decision == COUNCIL_DECISION_NEEDS_CHANGES

    def test_conflict_detected(self):
        decisions = [
            ExpertDecision(role=ROLE_SECURITY, display_name="Sec", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_BLOCKED, confidence=0.5, activated=True),
            ExpertDecision(role=ROLE_PRODUCT_UX, display_name="UX", authority=EXPERT_AUTHORITY_ADVISORY, decision=EXPERT_DECISION_APPROVED, confidence=0.9, activated=True),
        ]
        conflicts = detect_conflicts(decisions)
        assert len(conflicts) == 1
        assert conflicts[0].topic == "blocking_disagreement"

    def test_inactive_roles_excluded(self):
        decisions = [
            ExpertDecision(role=ROLE_SECURITY, display_name="Sec", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_APPROVED, confidence=1.0, activated=False),
            ExpertDecision(role=ROLE_QA, display_name="QA", authority=EXPERT_AUTHORITY_HARD_GATE, decision=EXPERT_DECISION_APPROVED, confidence=1.0, activated=True),
        ]
        summary = derive_council_summary(decisions)
        assert summary.active_roles_count == 1


class TestExpertCouncilService:
    def test_full_run_clean(self):
        svc = ExpertCouncilService()
        decisions, summary = svc.run_expert_reviews(
            changed_files=["backend/app/main.py"],
            safety_net={"tests_passed": True, "graphify_status": "updated", "error_count": 0},
            blast_radius={"impact_score": "low", "total_files_changed": 1},
            decision_gates={"verification_expectations": [], "graphify_expectations": {}},
        )
        assert len(decisions) == 5
        assert summary.overall_decision == COUNCIL_DECISION_READY

    def test_full_run_with_test_failure(self):
        svc = ExpertCouncilService()
        decisions, summary = svc.run_expert_reviews(
            changed_files=["backend/app/main.py"],
            safety_net={"tests_passed": False, "graphify_status": "updated", "error_count": 2, "verification_commands": []},
            blast_radius={"impact_score": "low", "total_files_changed": 1},
            decision_gates={"verification_expectations": ["pytest"], "graphify_expectations": {}},
        )
        assert summary.overall_decision == COUNCIL_DECISION_BLOCKED
        qa = next(d for d in decisions if d.role == ROLE_QA)
        assert qa.decision == EXPERT_DECISION_BLOCKED

    def test_expert_policy_override(self):
        svc = ExpertCouncilService()
        decisions, summary = svc.run_expert_reviews(
            changed_files=["backend/app/main.py"],
            safety_net={"tests_passed": True, "graphify_status": "updated", "error_count": 0},
            blast_radius={"impact_score": "low", "total_files_changed": 1},
            decision_gates={"verification_expectations": [], "graphify_expectations": {}},
            expert_policy={ROLE_PRODUCT_UX: {"disabled": True}},
        )
        assert len(decisions) == 4
        assert not any(d.role == ROLE_PRODUCT_UX for d in decisions)


async def _seed_factory_run_with_expert_data(repo: InMemoryRepository) -> dict:
    idea = Idea(title="Expert Council Test", slug="expert-council-test", description="Test", source_type="github_project")
    await repo.create_idea(idea)

    await repo.save_github_installation(GitHubInstallation(installation_id="200", account_login="testorg"))

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="200",
        owner="testorg",
        repo="expert-app",
        repo_full_name="testorg/expert-app",
        repo_url="https://github.com/testorg/expert-app",
        clone_url="https://github.com/testorg/expert-app.git",
        default_branch="main",
        detected_stack=["python", "fastapi"],
        test_commands=["pytest backend/tests"],
    )
    await repo.save_project_twin(project)

    template = TemplatePack(
        template_id="expert-test-template",
        version="1.0.0",
        channel="stable",
        display_name="Expert Test Template",
        description="Template for expert council tests",
        phases=[{"key": "build", "label": "Build"}],
        quality_gates=[],
        constraints=[],
        opencode_worker={"goal": "Build", "deliverables": [], "verification_commands": ["pytest backend/tests"]},
    )
    await repo.save_template_pack(template)

    await repo.save_template_artifact(TemplateArtifact(
        template_id="expert-test-template",
        artifact_key="AGENTS.md",
        content_type="text/markdown",
        uri="s3://templates/expert-test-template/AGENTS.md",
        content="# Standards",
    ))

    index = CodeIndexArtifact(
        project_id=project.id,
        idea_id=idea.id,
        commit_sha="abc456",
        file_inventory=[{"path": "backend/app/main.py", "size": 100, "kind": "source"}],
        test_commands=["pytest backend/tests"],
    )
    await repo.put_code_index(index)

    factory_run = FactoryRun(
        idea_id=project.idea_id,
        template_id="expert-test-template",
        status="running",
        config={"autonomy_level": "autonomous_development", "template_version": "1.0.0", "goal": "Test expert council"},
    )
    await repo.create_factory_run(factory_run)

    phase = FactoryPhase(factory_run_id=factory_run.id, phase_key="build", phase_order=1, status="running")
    await repo.save_factory_phase(phase)

    batch = FactoryBatch(factory_phase_id=phase.id, factory_run_id=factory_run.id, batch_key="build-1", status="completed")
    await repo.save_factory_batch(batch)

    work_item = WorkItem(
        idea_id=project.idea_id,
        project_id=project.id,
        job_type="agent_branch_work",
        status="completed",
        payload={"branch": "factory/test/build", "factory_run_id": factory_run.id, "factory_phase_id": phase.id, "factory_batch_id": batch.id},
        result={"tests_passed": True, "files_modified": ["backend/app/main.py"], "graphify_updated": True},
    )
    await repo.enqueue_work_item(work_item)
    batch.work_item_id = work_item.id
    await repo.save_factory_batch(batch)

    verification = VerificationRun(
        factory_batch_id=batch.id,
        factory_run_id=factory_run.id,
        verification_type="post_task",
        status="passed",
        result_summary="All tests passed",
        changed_files=["backend/app/main.py"],
        completed_at=utcnow(),
    )
    await repo.save_verification_run(verification)

    return {"idea": idea, "project": project, "template": template, "factory_run": factory_run}


@pytest.mark.asyncio
async def test_review_packet_contains_expert_reviews(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_expert_data(repo)
    fr = data["factory_run"]

    response = await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    assert response.status_code == 201
    packet = response.json()

    assert "expert_reviews" in packet
    assert isinstance(packet["expert_reviews"], list)
    assert len(packet["expert_reviews"]) == 5

    roles = {r["role"] for r in packet["expert_reviews"]}
    assert roles == {"security", "architecture_reliability", "privacy_data_protection", "qa_verification", "product_ux"}


@pytest.mark.asyncio
async def test_review_packet_contains_council_summary(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_expert_data(repo)
    fr = data["factory_run"]

    response = await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    assert response.status_code == 201
    packet = response.json()

    assert "council_summary" in packet
    summary = packet["council_summary"]
    assert summary["overall_decision"] in ("ready", "needs_changes", "blocked")
    assert isinstance(summary["active_roles_count"], int)
    assert isinstance(summary["unresolved_blockers_count"], int)
    assert isinstance(summary["conflict_count"], int)
    assert "highest_severity" in summary


@pytest.mark.asyncio
async def test_expert_reviews_persisted(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_expert_data(repo)
    fr = data["factory_run"]

    r1 = await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    assert r1.status_code == 201
    packet1 = r1.json()

    r2 = await test_client.get(f"/api/factory-runs/{fr.id}/review-packet")
    assert r2.status_code == 200
    packet2 = r2.json()

    assert packet2["expert_reviews"] == packet1["expert_reviews"]
    assert packet2["council_summary"] == packet1["council_summary"]


@pytest.mark.asyncio
async def test_expert_council_with_test_failures(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_expert_data(repo)
    fr = data["factory_run"]

    batch_id = None
    for batch in repo.factory_batches.values():
        if batch.factory_run_id == fr.id:
            batch_id = batch.id
            break

    failed_v = VerificationRun(
        factory_batch_id=batch_id,
        factory_run_id=fr.id,
        verification_type="post_task",
        status="failed",
        result_summary="Tests failed",
        failure_classification="test",
        changed_files=["backend/app/main.py"],
        command_output="FAILED",
        completed_at=utcnow(),
    )
    await repo.save_verification_run(failed_v)

    response = await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    assert response.status_code == 201
    packet = response.json()

    qa_review = next((r for r in packet["expert_reviews"] if r["role"] == "qa_verification"), None)
    assert qa_review is not None
    assert qa_review["decision"] == "blocked"
    assert packet["council_summary"]["overall_decision"] == "blocked"


@pytest.mark.asyncio
async def test_expert_council_with_security_sensitive_files(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_expert_data(repo)
    fr = data["factory_run"]

    batch_id = None
    for batch in repo.factory_batches.values():
        if batch.factory_run_id == fr.id:
            batch_id = batch.id
            break

    sec_v = VerificationRun(
        factory_batch_id=batch_id,
        factory_run_id=fr.id,
        verification_type="post_task",
        status="passed",
        result_summary="All passed",
        changed_files=["backend/app/auth/login.py", ".env", "backend/app/main.py"],
        completed_at=utcnow(),
    )
    await repo.save_verification_run(sec_v)

    response = await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    assert response.status_code == 201
    packet = response.json()

    sec_review = next((r for r in packet["expert_reviews"] if r["role"] == "security"), None)
    assert sec_review is not None
    assert sec_review["activated"] is True
    assert len(sec_review["triggers_matched"]) >= 1


@pytest.mark.asyncio
async def test_expert_council_list_includes_summary(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_expert_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.get("/api/review-packets")
    assert response.status_code == 200
    packets = response.json()["review_packets"]
    assert len(packets) == 1
    assert "council_summary" in packets[0]
    assert "expert_reviews" in packets[0]
