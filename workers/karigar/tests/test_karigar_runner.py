from __future__ import annotations

import json
from pathlib import Path

from karigar.commands import SafeCommandPolicy
from karigar.execution import CommandExecution
from karigar.models import JobStatus
from karigar.runner import KarigarRunner


class FakeRunner:
    def __init__(self, executions: dict[str, CommandExecution]) -> None:
        self.executions = executions

    def run(self, command: str, timeout_seconds: int, cwd: str | None = None, env: dict[str, str] | None = None) -> CommandExecution:
        return self.executions[command]


def _write_repo(root: Path) -> None:
    (root / ".git").mkdir()


def test_successful_run_writes_complete_artifacts(tmp_path: Path) -> None:
    _write_repo(tmp_path)
    runner = KarigarRunner(workspace=tmp_path, command_runner=FakeRunner({"python -m pytest": CommandExecution("python -m pytest", 0, "ok", "", 0.1)}))
    result = runner.run_job({"job_id": "job-1", "repository_path": str(tmp_path), "task_title": "Task", "task_prompt": "Prompt", "branch_name": "main", "engine_name": "mock", "command": "python -m pytest", "verification_commands": ["python -m pytest"]})
    job_dir = tmp_path / "artifacts" / "job-1"
    assert result.status == JobStatus.SUCCESS
    assert result.verification_results[0]["status"] == "passed"
    assert json.loads((job_dir / "result.json").read_text(encoding="utf-8"))["status"] == "success"
    assert (job_dir / "review.md").exists()


def test_validation_failure_missing_job_id_still_writes_result(tmp_path: Path) -> None:
    runner = KarigarRunner(workspace=tmp_path)
    result = runner.run_job({"repository_path": str(tmp_path), "task_title": "Task", "task_prompt": "Prompt"})
    job_dir = tmp_path / "artifacts" / ""
    assert result.status == JobStatus.FAILED
    assert result.failure_reason is not None
    assert (tmp_path / "artifacts" / "" / "result.json").exists()


def test_denied_command_blocking(tmp_path: Path) -> None:
    runner = KarigarRunner(workspace=tmp_path)
    result = runner.run_job({"job_id": "job-2", "repository_path": str(tmp_path), "task_title": "Task", "task_prompt": "Prompt", "branch_name": "main", "engine_name": "mock", "verification_commands": ["git merge main"]})
    assert result.verification_results[0]["status"] == "blocked"
    assert result.status == JobStatus.BLOCKED


def test_verification_capture(tmp_path: Path) -> None:
    runner = KarigarRunner(workspace=tmp_path, command_runner=FakeRunner({"pytest -q": CommandExecution("pytest -q", 1, "", "boom", 0.2)}))
    result = runner.run_job({"job_id": "job-3", "repository_path": str(tmp_path), "task_title": "Task", "task_prompt": "Prompt", "branch_name": "main", "engine_name": "mock", "verification_commands": ["pytest -q"], "allowed_commands": ["pytest"]})
    assert result.verification_results[0]["exit_code"] == 1
    assert result.verification_results[0]["stderr"] == "boom"
    assert result.verification_results[0]["duration_seconds"] == 0.2


def test_graphify_requirement_when_code_docs_changed(tmp_path: Path) -> None:
    _write_repo(tmp_path)
    class GraphifyRunner(KarigarRunner):
        def _detect_git_state(self, repo_root: Path):
            from karigar.git_state import GitState

            return GitState(root=repo_root, is_repo=True, changed_files=["notes.md"], dirty=True, code_or_docs_changed=True)

    runner = GraphifyRunner(workspace=tmp_path)
    result = runner.run_job({"job_id": "job-4", "repository_path": str(tmp_path), "task_title": "Task", "task_prompt": "Prompt", "branch_name": "main", "engine_name": "mock", "verification_commands": ["python -m pytest"]})
    assert result.failure_reason == "graphify_update_required"
    assert result.status == JobStatus.BLOCKED


def test_safe_command_policy() -> None:
    policy = SafeCommandPolicy()
    assert policy.is_allowed("python -m pytest")
    assert not policy.is_allowed("powershell Write-Host hi")
