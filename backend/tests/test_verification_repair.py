from __future__ import annotations

import pytest

from backend.app.config import settings
from backend.app.repository import (
    BLOCKED_STATUS,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    InMemoryRepository,
    Idea,
    ProjectTwin,
    RepairTask,
    VerificationRun,
    set_repository,
    utcnow,
)
from backend.app.services.verification_repair import (
    build_issue_summary,
    build_repair_prompt,
    classify_failure,
    process_verification_result,
)


@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


async def _seed_factory_run(repo: InMemoryRepository):
    idea = Idea(title="Repair Project", slug="repair-project", description="test")
    await repo.create_idea(idea)
    await repo.save_project_twin(ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="inst-1",
        owner="acme",
        repo="app",
        repo_full_name="acme/app",
        repo_url="https://github.com/acme/app",
        clone_url="https://github.com/acme/app.git",
        default_branch="main",
    ))
    run = await repo.create_factory_run(FactoryRun(idea_id=idea.id, template_id="tpl-1"))
    phase = await repo.save_factory_phase(FactoryPhase(
        factory_run_id=run.id, phase_key="build", phase_order=1,
    ))
    batch = await repo.save_factory_batch(FactoryBatch(
        factory_phase_id=phase.id, factory_run_id=run.id, batch_key="build-batch-1",
    ))
    return run, phase, batch


@pytest.mark.asyncio
async def test_verification_passed(repo):
    run, phase, batch = await _seed_factory_run(repo)
    result = await process_verification_result(
        factory_run_id=run.id,
        factory_batch_id=batch.id,
        passed=True,
        result={"summary": "All good", "tests_passed": True},
    )
    assert result["action"] == "verification_passed"

    verifications = await repo.list_verification_runs(batch.id)
    assert len(verifications) == 1
    assert verifications[0].status == "passed"

    repairs = await repo.list_repair_tasks(run.id)
    assert len(repairs) == 0


@pytest.mark.asyncio
async def test_verification_failed_creates_repair_task(repo):
    run, phase, batch = await _seed_factory_run(repo)
    result = await process_verification_result(
        factory_run_id=run.id,
        factory_batch_id=batch.id,
        passed=False,
        result={"test_output": "FAILED test_login - AssertionError: expected 200", "files_modified": ["src/auth.py"]},
    )
    assert result["action"] == "repair_created"
    assert result["failure_classification"] == "test"
    assert result["attempt_number"] == 1

    verifications = await repo.list_verification_runs(batch.id)
    assert len(verifications) == 1
    assert verifications[0].status == "failed"
    assert verifications[0].failure_classification == "test"

    repairs = await repo.list_repair_tasks(run.id)
    assert len(repairs) == 1
    assert repairs[0].status == "pending"
    assert repairs[0].failure_classification == "test"
    assert repairs[0].attempt_number == 1
    assert "src/auth.py" in repairs[0].changed_files
    assert repairs[0].work_item_id is not None

    work_item = await repo.get_work_item(repairs[0].work_item_id)
    assert work_item is not None
    assert work_item.job_type == "agent_branch_work"
    assert work_item.payload["role"] == "bug_fixer"
    assert work_item.payload["role_prompt_template"].startswith("Role: Bug Fixer")
    assert work_item.payload["repair_task_id"] == repairs[0].id
    assert work_item.payload["verifier_contract"]["role"] == "verifier"


@pytest.mark.asyncio
async def test_security_failure_blocks_immediately(repo):
    run, phase, batch = await _seed_factory_run(repo)
    result = await process_verification_result(
        factory_run_id=run.id,
        factory_batch_id=batch.id,
        passed=False,
        result={"test_output": "security violation: secret leaked in logs"},
    )
    assert result["action"] == "blocked_security"

    refreshed_run = await repo.get_factory_run(run.id)
    assert refreshed_run.status == BLOCKED_STATUS

    repairs = await repo.list_repair_tasks(run.id)
    assert len(repairs) == 1
    assert repairs[0].status == BLOCKED_STATUS
    assert repairs[0].failure_classification == "security"


@pytest.mark.asyncio
async def test_blocked_after_max_repair_attempts_per_task(repo):
    original_max = settings.max_repair_attempts_per_task
    settings.max_repair_attempts_per_task = 2
    try:
        run, phase, batch = await _seed_factory_run(repo)

        for i in range(2):
            result = await process_verification_result(
                factory_run_id=run.id,
                factory_batch_id=batch.id,
                passed=False,
                result={"test_output": f"FAILED iteration {i + 1}"},
            )
            assert result["action"] == "repair_created"

        result = await process_verification_result(
            factory_run_id=run.id,
            factory_batch_id=batch.id,
            passed=False,
            result={"test_output": "FAILED iteration 3"},
        )
        assert result["action"] == "blocked_max_attempts"

        refreshed_run = await repo.get_factory_run(run.id)
        assert refreshed_run.status == BLOCKED_STATUS

        repairs = await repo.list_repair_tasks(run.id)
        blocked_repairs = [r for r in repairs if r.status == BLOCKED_STATUS]
        assert len(blocked_repairs) == 1
        assert blocked_repairs[0].issue_summary != ""
        assert "BLOCKED" in blocked_repairs[0].issue_summary
    finally:
        settings.max_repair_attempts_per_task = original_max


@pytest.mark.asyncio
async def test_blocked_after_max_repair_attempts_per_batch(repo):
    original_task = settings.max_repair_attempts_per_task
    original_batch = settings.max_repair_attempts_per_batch
    settings.max_repair_attempts_per_task = 10
    settings.max_repair_attempts_per_batch = 2
    try:
        run, phase, batch = await _seed_factory_run(repo)

        phase2 = await repo.save_factory_phase(FactoryPhase(
            factory_run_id=run.id, phase_key="test", phase_order=2,
        ))
        batch2 = await repo.save_factory_batch(FactoryBatch(
            factory_phase_id=phase2.id, factory_run_id=run.id, batch_key="test-batch-1",
        ))

        await process_verification_result(
            factory_run_id=run.id,
            factory_batch_id=batch.id,
            passed=False,
            result={"test_output": "FAILED batch1"},
        )
        await process_verification_result(
            factory_run_id=run.id,
            factory_batch_id=batch2.id,
            passed=False,
            result={"test_output": "FAILED batch2"},
        )

        result = await process_verification_result(
            factory_run_id=run.id,
            factory_batch_id=batch.id,
            passed=False,
            result={"test_output": "FAILED batch1 again"},
        )
        assert result["action"] == "blocked_max_attempts"
        assert result["run_attempts"] >= 2

        refreshed_run = await repo.get_factory_run(run.id)
        assert refreshed_run.status == BLOCKED_STATUS
    finally:
        settings.max_repair_attempts_per_task = original_task
        settings.max_repair_attempts_per_batch = original_batch


def test_classify_failure_test():
    assert classify_failure("FAILED test_login - AssertionError") == "test"
    assert classify_failure("2 failed, 10 passed") == "test"


def test_classify_failure_build():
    assert classify_failure("compilation error in main.rs") == "build"


def test_classify_failure_lint():
    assert classify_failure("ruff: E501 line too long") == "lint"


def test_classify_failure_type():
    assert classify_failure("mypy: error: Incompatible types") == "type"


def test_classify_failure_security():
    assert classify_failure("security violation: CVE-2024-1234 detected") == "security"


def test_classify_failure_dependency():
    assert classify_failure("ModuleNotFoundError: No module named 'foo'") == "dependency"


def test_classify_failure_ambiguous():
    assert classify_failure("something went wrong") == "ambiguous"


def test_classify_failure_migration():
    assert classify_failure("alembic migration failed") == "migration"


def test_classify_failure_runtime():
    assert classify_failure("RuntimeError: segfault") == "runtime"


def test_classify_failure_integration():
    assert classify_failure("E2E test: connection refused on port 8080") == "integration"


def test_classify_failure_flaky():
    assert classify_failure("timeout after 30s, possible race condition") == "flaky"


def test_build_issue_summary():
    summary = build_issue_summary(
        failure_classification="test",
        command_output="FAILED test_x\nAssertionError",
        attempt_number=3,
        batch_key="build-batch-1",
        factory_run_id="run-abc",
        changed_files=["src/a.py", "src/b.py"],
    )
    assert "[BLOCKED]" in summary
    assert "test" in summary
    assert "run-abc" in summary
    assert "build-batch-1" in summary
    assert "Attempt: 3" in summary
    assert "src/a.py" in summary


def test_build_repair_prompt():
    prompt = build_repair_prompt(
        failure_classification="lint",
        command_output="ruff: E501 line too long",
        recent_diff="diff --git a/file.py",
        changed_files=["file.py"],
        acceptance_criteria=["ruff check passes"],
        attempt_number=2,
        batch_key="lint-batch-1",
    )
    assert "attempt 2" in prompt
    assert "lint" in prompt
    assert "ruff" in prompt
    assert "file.py" in prompt
    assert "Guardrails" in prompt
    assert "Do not delete tests" in prompt


@pytest.mark.asyncio
async def test_repair_task_crud(repo):
    task = RepairTask(
        factory_run_id="run-1",
        factory_batch_id="batch-1",
        failure_classification="test",
        command_output="FAILED",
        attempt_number=1,
    )
    saved = await repo.save_repair_task(task)
    assert saved.id
    assert saved.status == "pending"

    fetched = await repo.get_repair_task(saved.id)
    assert fetched is not None
    assert fetched.failure_classification == "test"

    tasks = await repo.list_repair_tasks("run-1")
    assert len(tasks) == 1

    batch_tasks = await repo.list_repair_tasks_for_batch("batch-1")
    assert len(batch_tasks) == 1

    batch_tasks_empty = await repo.list_repair_tasks_for_batch("batch-2")
    assert len(batch_tasks_empty) == 0

    saved.status = "completed"
    saved.completed_at = utcnow()
    await repo.save_repair_task(saved)

    refreshed = await repo.get_repair_task(saved.id)
    assert refreshed is not None
    assert refreshed.status == "completed"

    filtered = await repo.list_repair_tasks("run-1", statuses={"pending"})
    assert len(filtered) == 0
    filtered2 = await repo.list_repair_tasks("run-1", statuses={"completed"})
    assert len(filtered2) == 1


@pytest.mark.asyncio
async def test_verification_run_has_classification_fields(repo):
    run, phase, batch = await _seed_factory_run(repo)
    vr = VerificationRun(
        factory_batch_id=batch.id,
        factory_run_id=run.id,
        verification_type="post_task",
        status="failed",
        failure_classification="test",
        command_output="FAILED test_x",
        changed_files=["src/x.py"],
        result_summary="1 failed",
        completed_at=utcnow(),
    )
    saved = await repo.save_verification_run(vr)
    fetched = await repo.get_verification_run(saved.id)
    assert fetched is not None
    assert fetched.failure_classification == "test"
    assert fetched.command_output == "FAILED test_x"
    assert fetched.changed_files == ["src/x.py"]


@pytest.mark.asyncio
async def test_process_verification_result_run_not_found(repo):
    result = await process_verification_result(
        factory_run_id="nonexistent",
        factory_batch_id="nonexistent",
        passed=True,
        result={},
    )
    assert result["action"] == "noop"
