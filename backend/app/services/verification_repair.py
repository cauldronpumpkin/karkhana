from __future__ import annotations

import re
from typing import Any

from backend.app.config import settings
from backend.app.repository import (
    BLOCKED_STATUS,
    FAILURE_CLASSIFICATIONS,
    SECURITY_FAILURE,
    FactoryBatch,
    FactoryRun,
    RepairTask,
    VerificationRun,
    get_repository,
    utcnow,
)
from backend.app.services.autonomy import can_bypass_repair_limits
from backend.app.services.ai_roles import FactoryRole, RolePromptBuilder
from backend.app.services.project_twin import ProjectTwinService, to_jsonable

_KEYWORD_MAP: dict[str, list[str]] = {
    "security": [
        r"\bsecurity\s+violation\b", r"\bvulnerability\b",
        r"\bCVE-\d{4}-\d+\b", r"\bsecret\b.*\bleaked?\b",
        r"\bcredential[s]?\b.*\bexposed?\b", r"\bOWASP\b",
    ],
    "migration": [
        r"\bmigration\b", r"\balembic\b", r"\bdjango\.db\b",
        r"\bschema\s+change\b", r"\bALTER\s+TABLE\b",
    ],
    "dependency": [
        r"\bModuleNotFoundError\b", r"\bImportError\b",
        r"\bpackage\s+not\s+found\b", r"\bdependency\b.*\bconflict\b",
        r"\bpip\b.*\berror\b", r"\bnpm\b.*\bERR!\b",
    ],
    "build": [
        r"\bcompilation\s+error\b", r"\bbuild\s+(fail|error)",
        r"\bcargo\s+build\b.*error", r"\bgcc\b.*error",
        r"\bwebpack\b.*error", r"\bvite\b.*error",
    ],
    "lint": [
        r"\blint\b", r"\beslint\b", r"\bruff\b", r"\bflake8\b",
        r"\bpylint\b", r"\bstyle\s+error\b",
    ],
    "type": [
        r"\btype\s*error\b", r"\bTypeErr(or)?\b",
        r"\bmypy\b.*error", r"\btypescript\b.*error",
        r"\btypecheck\b", r"\bTS\d{4}\b",
    ],
    "integration": [
        r"\bintegration\s+test\b", r"\bE2E\b",
        r"\bconnection\s*(refused|timeout|error)\b",
        r"\b50[0-3]\b",
    ],
    "flaky": [
        r"\btimeout\b", r"\bdeadlock\b", r"\brace\s+condition\b",
        r"\bintermittent\b", r"\bflaky\b",
    ],
    "runtime": [
        r"\bRuntimeError\b", r"\bException\b", r"\btraceback\b",
        r"\bsegfault\b", r"\bOOM\b", r"\bmemory\s+error\b",
    ],
    "test": [
        r"\bFAILED\b", r"\bfailure[s]?\b", r"\bassert\b", r"\bAssertionError\b",
        r"\bpytest\b", r"\bjest\b", r"\btest[s]?\s+(fail|error)",
        r"\b\d+\s+failed\b",
    ],
}

_DEFAULT_GUARDRAILS = [
    "Do not delete tests to make them pass.",
    "Do not refactor unrelated code.",
    "Make the smallest safe fix that addresses the root cause.",
    "Preserve existing test expectations unless the test itself is incorrect.",
]


def classify_failure(command_output: str, verification_type: str = "") -> str:
    text = f"{verification_type}\n{command_output}".lower()
    for classification, patterns in _KEYWORD_MAP.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return classification
    return "ambiguous"


def build_issue_summary(
    *,
    failure_classification: str,
    command_output: str,
    attempt_number: int,
    batch_key: str,
    factory_run_id: str,
    changed_files: list[str] | None = None,
) -> str:
    changed = changed_files or []
    files_note = ""
    if changed:
        files_note = f"\nChanged files: {', '.join(changed[:10])}"
    truncated_output = command_output[:2000] if command_output else "(no output)"
    return (
        f"[BLOCKED] Factory run {factory_run_id}, batch '{batch_key}'\n"
        f"Failure type: {failure_classification}\n"
        f"Attempt: {attempt_number}\n"
        f"Output:\n{truncated_output}"
        f"{files_note}\n\n"
        f"This task has been blocked after exhausting all repair attempts. "
        f"Manual intervention required."
    )


def build_repair_prompt(
    *,
    failure_classification: str,
    command_output: str,
    recent_diff: str,
    changed_files: list[str],
    acceptance_criteria: list[str],
    attempt_number: int,
    batch_key: str,
) -> str:
    criteria_text = "\n".join(f"- {c}" for c in acceptance_criteria) or "- All existing tests pass."
    guardrails_text = "\n".join(f"- {g}" for g in _DEFAULT_GUARDRAILS)
    truncated_output = command_output[:4000] if command_output else "(no output captured)"
    truncated_diff = recent_diff[:3000] if recent_diff else "(no diff available)"
    files_text = ", ".join(changed_files[:20]) if changed_files else "(none detected)"
    return f"""Repair Task (attempt {attempt_number})

Failure classification: {failure_classification}
Batch: {batch_key}

Failing command output:
{truncated_output}

Recent diff:
{truncated_diff}

Changed files: {files_text}

Acceptance criteria:
{criteria_text}

Guardrails (MUST follow):
{guardrails_text}

Instructions:
1. Analyze the failure output above to identify the root cause.
2. Make the MINIMUM change needed to fix the issue.
3. Do NOT refactor code unrelated to the failure.
4. Do NOT delete or skip tests to make them pass.
5. Run the verification commands to confirm the fix.
6. Report files modified and test results.
""".strip()


async def _enqueue_bug_fixer_work_item(
    *,
    repo: Any,
    run: FactoryRun,
    batch: FactoryBatch,
    task: RepairTask,
) -> dict[str, Any]:
    project = await repo.get_project_twin(run.idea_id)
    if not project:
        return {
            "work_item": None,
            "repair_contract": None,
            "verifier_contract": None,
        }

    graphify_instructions = {
        "pre_task": [
            "Read graphify-out/GRAPH_REPORT.md for god nodes and community structure",
            "Read graphify-out/wiki/index.md if it exists for codebase navigation",
        ],
        "post_task": [
            "Run 'graphify update .' after all code changes to keep the knowledge graph current",
        ],
    }
    branch_name = f"factory/{run.id[:8]}/{batch.batch_key}/repair-{task.attempt_number}"
    repair_contract = RolePromptBuilder.build(
        FactoryRole.BUG_FIXER,
        {
            "project": to_jsonable(project),
            "factory_run_id": run.id,
            "batch": to_jsonable(batch),
            "batch_key": batch.batch_key,
            "failure_classification": task.failure_classification,
            "command_output": task.command_output,
            "recent_diff": task.recent_diff or task.command_output or "",
            "changed_files": task.changed_files,
            "acceptance_criteria": task.acceptance_criteria,
            "attempt_number": task.attempt_number,
            "graphify_instructions": graphify_instructions,
        },
    )
    verifier_contract = RolePromptBuilder.build(
        FactoryRole.VERIFIER,
        {
            "project": to_jsonable(project),
            "factory_run_id": run.id,
            "factory_batch_id": batch.id,
            "verification_commands": task.acceptance_criteria or ["All existing tests pass."],
            "expected_result_fields": list(repair_contract["output_schema"].get("properties", {}).keys()),
        },
    )

    project_service = ProjectTwinService()
    work_item = await project_service.enqueue_job(
        idea_id=run.idea_id,
        project_id=project.id,
        job_type="agent_branch_work",
        payload={
            "role": repair_contract["role"],
            "role_prompt": repair_contract["prompt"],
            "role_prompt_template": repair_contract["prompt_template"],
            "role_required_inputs": repair_contract["required_inputs"],
            "role_output_schema": repair_contract["output_schema"],
            "role_provider": repair_contract["provider"],
            "role_model": repair_contract["model"],
            "messages": repair_contract["messages"],
            "prompt": repair_contract["prompt"],
            "factory_run_id": run.id,
            "factory_phase_id": batch.factory_phase_id,
            "factory_batch_id": batch.id,
            "repair_task_id": task.id,
            "factory_job_type": "factory_repair",
            "execution_type": "agent_branch_work",
            "project_twin": {
                "project_id": project.id,
                "idea_id": project.idea_id,
                "provider": project.provider,
                "owner": project.owner,
                "repo": project.repo,
                "repo_full_name": project.repo_full_name,
                "clone_url": project.clone_url,
                "default_branch": project.default_branch,
                "detected_stack": project.detected_stack,
            },
            "branch": branch_name,
            "base_branch": project.default_branch,
            "batch_key": batch.batch_key,
            "failure_classification": task.failure_classification,
            "command_output": task.command_output,
            "recent_diff": task.recent_diff,
            "changed_files": task.changed_files,
            "acceptance_criteria": task.acceptance_criteria,
            "attempt_number": task.attempt_number,
            "graphify_instructions": graphify_instructions,
            "verifier_contract": verifier_contract,
        },
        idempotency_key=f"factory:{run.id}:repair:{batch.id}:{task.attempt_number}",
        priority=60,
    )
    task.work_item_id = work_item.id
    await repo.save_repair_task(task)
    return {
        "work_item": work_item,
        "repair_contract": repair_contract,
        "verifier_contract": verifier_contract,
    }


async def process_verification_result(
    *,
    factory_run_id: str,
    factory_batch_id: str,
    passed: bool,
    result: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:
    repo = get_repository()
    run = await repo.get_factory_run(factory_run_id)
    if not run:
        return {"action": "noop", "reason": "run_not_found"}

    batch = await repo.get_factory_batch(factory_batch_id)
    if not batch:
        return {"action": "noop", "reason": "batch_not_found"}

    command_output = (result.get("test_output") or error or "")
    changed_files = result.get("files_modified") or []

    verification = VerificationRun(
        factory_batch_id=factory_batch_id,
        factory_run_id=factory_run_id,
        verification_type="post_task",
        status="passed" if passed else "failed",
        command_output=command_output,
        changed_files=changed_files,
        completed_at=utcnow(),
    )

    if passed:
        verification.result_summary = result.get("summary") or "All verification commands passed."
        await repo.save_verification_run(verification)
        return {"action": "verification_passed", "verification_id": verification.id}

    verification.failure_classification = classify_failure(
        command_output=command_output,
        verification_type="post_task",
    )
    verification.result_summary = (
        result.get("summary") or error or f"Verification failed: {verification.failure_classification}"
    )
    await repo.save_verification_run(verification)

    if verification.failure_classification == SECURITY_FAILURE:
        run.status = BLOCKED_STATUS
        await repo.save_factory_run(run)

        task = RepairTask(
            factory_run_id=factory_run_id,
            factory_batch_id=factory_batch_id,
            failure_classification=SECURITY_FAILURE,
            status=BLOCKED_STATUS,
            command_output=command_output,
            changed_files=changed_files,
            acceptance_criteria=["Fix all security violations before proceeding."],
            guardrails=_DEFAULT_GUARDRAILS,
            issue_summary=build_issue_summary(
                failure_classification=SECURITY_FAILURE,
                command_output=command_output,
                attempt_number=1,
                batch_key=batch.batch_key,
                factory_run_id=factory_run_id,
                changed_files=changed_files,
            ),
        )
        await repo.save_repair_task(task)
        return {
            "action": "blocked_security",
            "verification_id": verification.id,
            "repair_task_id": task.id,
        }

    existing_repairs = await repo.list_repair_tasks_for_batch(factory_batch_id)
    task_attempts = len([r for r in existing_repairs if r.status != "cancelled"])
    run_repairs = await repo.list_repair_tasks(factory_run_id, statuses={"pending", "completed", "blocked"})
    run_attempts = len(run_repairs)

    if not can_bypass_repair_limits(run):
        if task_attempts >= settings.max_repair_attempts_per_task or run_attempts >= settings.max_repair_attempts_per_batch:
            run.status = BLOCKED_STATUS
            await repo.save_factory_run(run)

            task = RepairTask(
                factory_run_id=factory_run_id,
                factory_batch_id=factory_batch_id,
                failure_classification=verification.failure_classification,
                status=BLOCKED_STATUS,
                attempt_number=task_attempts + 1,
                command_output=command_output,
                changed_files=changed_files,
                acceptance_criteria=["All verification commands pass."],
                guardrails=_DEFAULT_GUARDRAILS,
                issue_summary=build_issue_summary(
                    failure_classification=verification.failure_classification,
                    command_output=command_output,
                    attempt_number=task_attempts + 1,
                    batch_key=batch.batch_key,
                    factory_run_id=factory_run_id,
                    changed_files=changed_files,
                ),
            )
            await repo.save_repair_task(task)
            return {
                "action": "blocked_max_attempts",
                "verification_id": verification.id,
                "repair_task_id": task.id,
                "task_attempts": task_attempts,
                "run_attempts": run_attempts,
            }

    acceptance_criteria = []
    for cmd in (result.get("verification_commands") or []):
        acceptance_criteria.append(f"`{cmd}` exits with code 0")
    if not acceptance_criteria:
        acceptance_criteria = ["All existing tests pass."]

    task = RepairTask(
        factory_run_id=factory_run_id,
        factory_batch_id=factory_batch_id,
        failure_classification=verification.failure_classification,
        status="pending",
        attempt_number=task_attempts + 1,
        command_output=command_output,
        recent_diff=result.get("recent_diff", ""),
        changed_files=changed_files,
        acceptance_criteria=acceptance_criteria,
        guardrails=_DEFAULT_GUARDRAILS,
        issue_summary="",
    )
    await repo.save_repair_task(task)
    await _enqueue_bug_fixer_work_item(repo=repo, run=run, batch=batch, task=task)

    return {
        "action": "repair_created",
        "verification_id": verification.id,
        "repair_task_id": task.id,
        "failure_classification": verification.failure_classification,
        "attempt_number": task.attempt_number,
    }
