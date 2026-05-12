from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from karigar.auto_repair import (
    AutoRepairEngine,
    FailureClass,
    RepairAction,
    RepairAttempt,
)
from karigar.commands import RealEnginePolicy, SafeCommandPolicy
from karigar.engines import (
    HermesAgentEngine,
    MockEngine,
    OpenCodeEngine,
    _ENGINE_REGISTRY,
    get_engine,
)
from karigar.models import JobContract, JobResult, JobStatus
from karigar.runner import KarigarRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(
    returncode: int = 0,
    stdout: str = "mock output",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def _make_job(
    job_id: str = "test-job",
    repository_path: str = ".",
    task_title: str = "Test Task",
    task_prompt: str = "test prompt",
    branch_name: str = "main",
    engine_name: str = "mock",
    **kwargs,
) -> JobContract:
    return JobContract(
        job_id=job_id,
        repository_path=repository_path,
        task_title=task_title,
        task_prompt=task_prompt,
        branch_name=branch_name,
        engine_name=engine_name,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Test 1: Engine registry contains all engines
# ---------------------------------------------------------------------------


def test_engine_registry_contains_all_engines() -> None:
    """Verify get_engine works for mock, opencode, hermes and raises for unknown."""
    assert "mock" in _ENGINE_REGISTRY
    assert "opencode" in _ENGINE_REGISTRY
    assert "hermes" in _ENGINE_REGISTRY

    mock_engine = get_engine("mock")
    assert isinstance(mock_engine, MockEngine)
    assert mock_engine.engine_name == "mock"

    opencode_engine = get_engine("opencode")
    assert isinstance(opencode_engine, OpenCodeEngine)
    assert opencode_engine.engine_name == "opencode"

    hermes_engine = get_engine("hermes")
    assert isinstance(hermes_engine, HermesAgentEngine)
    assert hermes_engine.engine_name == "hermes"

    with pytest.raises(ValueError, match="Unknown engine: unknown"):
        get_engine("unknown")

    # Verify each get_engine call returns a fresh instance
    a = get_engine("mock")
    b = get_engine("mock")
    assert a is not b
    assert isinstance(a, MockEngine) and isinstance(b, MockEngine)


# ---------------------------------------------------------------------------
# Test 2: Mock engine still works
# ---------------------------------------------------------------------------


def test_mock_engine_still_works() -> None:
    """Verify MockEngine produces the expected SUCCESS result for a basic job."""
    engine = MockEngine()
    job = _make_job(
        job_id="test-mock",
        task_title="Mock Test",
        task_prompt="Run mock",
        engine_name="mock",
        command="python -m pytest",
    )
    result = engine.run(job)
    assert isinstance(result, JobResult)
    assert result.status == JobStatus.SUCCESS
    assert result.engine_used == "mock"
    assert result.return_code == 0
    assert result.command == "python -m pytest"
    assert "mocked:" in result.stdout


def test_mock_engine_blocks_missing_command() -> None:
    """MockEngine should BLOCKED when no command is provided."""
    engine = MockEngine()
    job = _make_job(job_id="test-no-cmd", engine_name="mock", command="")
    result = engine.run(job)
    assert result.status == JobStatus.BLOCKED
    assert result.blocked_reason == "missing_command"


def test_mock_engine_blocks_unsafe_command() -> None:
    """MockEngine should BLOCKED when command is denied by policy."""
    engine = MockEngine()
    job = _make_job(job_id="test-unsafe", engine_name="mock", command="rm -rf /")
    result = engine.run(job)
    assert result.status == JobStatus.BLOCKED
    assert result.blocked_reason == "unsafe_command"


# ---------------------------------------------------------------------------
# Test 3: OpenCode engine blocks on empty prompt
# ---------------------------------------------------------------------------


def test_opencode_engine_blocks_on_empty_prompt() -> None:
    """OpenCodeEngine returns BLOCKED when task_prompt is empty."""
    engine = OpenCodeEngine()
    job = _make_job(
        job_id="test-oc-block",
        task_prompt="",
        engine_name="opencode",
    )
    result = engine.run(job)
    assert result.status == JobStatus.BLOCKED
    assert result.blocked_reason == "missing_task_prompt"
    assert result.engine_used == "opencode"
    assert result.summary == "No task prompt provided"


# ---------------------------------------------------------------------------
# Test 4: Hermes engine blocks on empty prompt
# ---------------------------------------------------------------------------


def test_hermes_engine_blocks_on_empty_prompt() -> None:
    """HermesAgentEngine returns BLOCKED when task_prompt is empty."""
    engine = HermesAgentEngine()
    job = _make_job(
        job_id="test-hermes-block",
        task_prompt="",
        engine_name="hermes",
    )
    result = engine.run(job)
    assert result.status == JobStatus.BLOCKED
    assert result.blocked_reason == "missing_task_prompt"
    assert result.engine_used == "hermes"
    assert result.summary == "No task prompt provided"


# ---------------------------------------------------------------------------
# Test 5: OpenCode engine builds correct command
# ---------------------------------------------------------------------------


def test_opencode_engine_builds_correct_command(monkeypatch) -> None:
    """Verify OpenCodeEngine invokes subprocess.run with the right command."""
    captured_commands: list[tuple[str | list[str], bool]] = []

    def fake_run(command, **kwargs):
        captured_commands.append((command, kwargs.get("shell", False)))
        return _make_completed_process()

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = OpenCodeEngine()
    job = _make_job(
        job_id="test-oc-cmd",
        repository_path="/tmp/repo",
        task_prompt="fix bug in auth.py",
        engine_name="opencode",
    )
    result = engine.run(job)

    assert result.status == JobStatus.SUCCESS
    assert result.engine_used == "opencode"
    assert result.command is not None

    # First subprocess.run call should be the opencode command
    assert len(captured_commands) >= 1
    first_command, shell_flag = captured_commands[0]
    assert isinstance(first_command, str)
    assert "opencode run" in first_command
    assert "fix bug in auth.py" in first_command
    assert shell_flag is True


def test_opencode_engine_fallback_to_chat(monkeypatch) -> None:
    """When opencode run fails, the engine falls back to opencode chat."""
    captured_commands: list[str] = []
    call_count = {"count": 0}

    def fake_run(command, **kwargs):
        call_count["count"] += 1
        captured_commands.append(command if isinstance(command, str) else " ".join(command))
        if call_count["count"] == 1:
            # First call (opencode run) fails
            return _make_completed_process(returncode=1, stderr="opencode: run not found")
        # Subsequent calls (fallback chat + git calls) succeed
        return _make_completed_process()

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = OpenCodeEngine()
    job = _make_job(
        job_id="test-oc-fallback",
        task_prompt="fix bug in auth.py",
        engine_name="opencode",
    )
    result = engine.run(job)

    assert result.status == JobStatus.SUCCESS
    assert result.engine_used == "opencode"
    assert "opencode run" in captured_commands[0]
    assert "opencode chat" in captured_commands[1]


def test_opencode_engine_reports_failure(monkeypatch) -> None:
    """When both opencode run and chat fail, engine reports FAILED."""
    def fake_run(command, **kwargs):
        return _make_completed_process(returncode=1, stderr="all attempts failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = OpenCodeEngine()
    job = _make_job(
        job_id="test-oc-fail",
        task_prompt="fix bug",
        engine_name="opencode",
    )
    result = engine.run(job)

    assert result.status == JobStatus.FAILED
    assert result.engine_used == "opencode"
    assert result.return_code == 1
    assert "all attempts failed" in (result.stderr or "")


def test_opencode_engine_times_out(monkeypatch) -> None:
    """When subprocess.run raises TimeoutExpired, engine returns TIMED_OUT."""
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = OpenCodeEngine()
    job = _make_job(
        job_id="test-oc-timeout",
        task_prompt="fix bug",
        engine_name="opencode",
    )
    result = engine.run(job)

    assert result.status == JobStatus.TIMED_OUT
    assert result.engine_used == "opencode"


# ---------------------------------------------------------------------------
# Test 6: Hermes engine respects model from metadata
# ---------------------------------------------------------------------------


def test_hermes_engine_respects_model_from_metadata(monkeypatch) -> None:
    """HermesAgentEngine uses metadata['hermes_model'] when available."""
    captured_commands: list[str] = []

    def fake_run(command, **kwargs):
        if isinstance(command, str):
            captured_commands.append(command)
        return _make_completed_process()

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = HermesAgentEngine()
    job = _make_job(
        job_id="test-hermes-model-meta",
        task_prompt="Add rate limiting",
        engine_name="hermes",
        metadata={"hermes_model": "gpt-5.4-mini"},
    )
    result = engine.run(job)

    assert result.status == JobStatus.SUCCESS
    assert result.engine_used == "hermes"

    # First subprocess.run call should contain the model flag
    assert len(captured_commands) >= 1
    first_command = captured_commands[0]
    assert "hermes chat -m gpt-5.4-mini" in first_command


# ---------------------------------------------------------------------------
# Test 7: Hermes engine falls back to payload for model
# ---------------------------------------------------------------------------


def test_hermes_engine_falls_back_to_payload_for_model(monkeypatch) -> None:
    """Without metadata, HermesAgentEngine uses payload['hermes_model']."""
    captured_commands: list[str] = []

    def fake_run(command, **kwargs):
        if isinstance(command, str):
            captured_commands.append(command)
        return _make_completed_process()

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = HermesAgentEngine()
    job = _make_job(
        job_id="test-hermes-model-payload",
        task_prompt="Add rate limiting",
        engine_name="hermes",
        payload={"hermes_model": "deepseek-v4-pro"},
    )
    result = engine.run(job)

    assert result.status == JobStatus.SUCCESS
    assert result.engine_used == "hermes"

    first_command = captured_commands[0]
    assert "hermes chat -m deepseek-v4-pro" in first_command


def test_hermes_engine_no_model_specified(monkeypatch) -> None:
    """HermesAgentEngine works without any model specified in metadata/payload."""
    captured_commands: list[str] = []

    def fake_run(command, **kwargs):
        if isinstance(command, str):
            captured_commands.append(command)
        return _make_completed_process()

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = HermesAgentEngine()
    job = _make_job(
        job_id="test-hermes-no-model",
        task_prompt="Do something",
        engine_name="hermes",
    )
    result = engine.run(job)

    assert result.status == JobStatus.SUCCESS
    assert result.engine_used == "hermes"

    first_command = captured_commands[0]
    assert "hermes chat -q" in first_command
    assert "-m" not in first_command


def test_hermes_engine_metadata_overrides_payload(monkeypatch) -> None:
    """metadata['hermes_model'] takes priority over payload['hermes_model']."""
    captured_commands: list[str] = []

    def fake_run(command, **kwargs):
        if isinstance(command, str):
            captured_commands.append(command)
        return _make_completed_process()

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = HermesAgentEngine()
    job = _make_job(
        job_id="test-hermes-override",
        task_prompt="Refactor module",
        engine_name="hermes",
        metadata={"hermes_model": "meta-model"},
        payload={"hermes_model": "payload-model"},
    )
    result = engine.run(job)

    assert result.status == JobStatus.SUCCESS
    first_command = captured_commands[0]
    assert "hermes chat -m meta-model" in first_command
    assert "payload-model" not in first_command


def test_hermes_engine_reports_failure(monkeypatch) -> None:
    """HermesAgentEngine returns FAILED on non-zero exit."""
    def fake_run(command, **kwargs):
        return _make_completed_process(returncode=1, stderr="hermes: internal error")

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = HermesAgentEngine()
    job = _make_job(
        job_id="test-hermes-fail",
        task_prompt="Do something",
        engine_name="hermes",
    )
    result = engine.run(job)

    assert result.status == JobStatus.FAILED
    assert result.engine_used == "hermes"
    assert result.return_code == 1


def test_hermes_engine_times_out(monkeypatch) -> None:
    """HermesAgentEngine returns TIMED_OUT on timeout."""
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)

    engine = HermesAgentEngine()
    job = _make_job(
        job_id="test-hermes-timeout",
        task_prompt="Do something",
        engine_name="hermes",
    )
    result = engine.run(job)

    assert result.status == JobStatus.TIMED_OUT
    assert result.engine_used == "hermes"


# ---------------------------------------------------------------------------
# Test 8: Runner dispatches to real engine
# ---------------------------------------------------------------------------


def test_runner_dispatches_to_real_engine(monkeypatch) -> None:
    """Verify engine dispatch based on engine_name routes to the correct engine."""

    def fake_run(command, **kwargs):
        return _make_completed_process()

    monkeypatch.setattr(subprocess, "run", fake_run)

    # OpenCode engine via get_engine dispatcher
    opencode_engine = get_engine("opencode")
    opencode_job = _make_job(
        job_id="test-dispatch-oc",
        task_prompt="fix bug",
        engine_name="opencode",
    )
    opencode_result = opencode_engine.run(opencode_job)
    assert opencode_result.engine_used == "opencode"
    assert opencode_result.status == JobStatus.SUCCESS

    # Hermes engine via get_engine dispatcher
    hermes_engine = get_engine("hermes")
    hermes_job = _make_job(
        job_id="test-dispatch-h",
        task_prompt="fix bug",
        engine_name="hermes",
    )
    hermes_result = hermes_engine.run(hermes_job)
    assert hermes_result.engine_used == "hermes"
    assert hermes_result.status == JobStatus.SUCCESS

    # Mock engine via get_engine dispatcher
    mock_engine = get_engine("mock")
    mock_job = _make_job(
        job_id="test-dispatch-m",
        task_prompt="do something",
        engine_name="mock",
        command="python -m pytest",
    )
    mock_result = mock_engine.run(mock_job)
    assert mock_result.engine_used == "mock"
    assert mock_result.status == JobStatus.SUCCESS

    # Verify the get_engine dispatcher maps correctly for all known engines
    for engine_name in ("opencode", "hermes", "mock"):
        engine = get_engine(engine_name)
        assert engine.engine_name == engine_name


# ---------------------------------------------------------------------------
# Test 9: Runner uses system runner for real engines
# ---------------------------------------------------------------------------


def test_runner_uses_system_runner_for_real_engines(tmp_path: Path, monkeypatch) -> None:
    """Verify the code path doesn't crash with real engine names and verification commands.

    KarigarRunner defaults to MockCommandRunner for verifications. This test
    ensures that passing engine_name='opencode' or 'hermes' through the runner
    pipeline does not break anything even when opencode/hermes are not installed.
    """
    import subprocess as sp

    def fake_run(command, **kwargs):
        return sp.CompletedProcess([], 0, stdout="mock output", stderr="")

    monkeypatch.setattr(sp, "run", fake_run)

    from karigar.execution import MockCommandRunner
    runner = KarigarRunner(workspace=tmp_path, command_runner=MockCommandRunner())

    for engine_name in ("opencode", "hermes"):
        job_data = {
            "job_id": f"test-real-{engine_name}",
            "repository_path": str(tmp_path),
            "task_title": "Real Engine Test",
            "task_prompt": "test task",
            "branch_name": "main",
            "engine_name": engine_name,
            # No verification commands — this test is about engine dispatch, not verification
        }
        result = runner.run_job(job_data)
        assert result is not None
        assert result.job_id == f"test-real-{engine_name}"
        assert result.started_at is not None
        assert result.completed_at is not None


# ---------------------------------------------------------------------------
# Test 10: Runner still uses mock runner for mock engine
# ---------------------------------------------------------------------------


def test_runner_still_uses_mock_runner_for_mock_engine(tmp_path: Path) -> None:
    """KarigarRunner._base_result() returns a MockEngine result by default."""
    runner = KarigarRunner(workspace=tmp_path)
    job_data = {
        "job_id": "test-mock-runner",
        "repository_path": str(tmp_path),
        "task_title": "Mock Runner Test",
        "task_prompt": "mock test",
        "branch_name": "main",
        "engine_name": "mock",
        "command": "python -m pytest",
        "verification_commands": ["python -m pytest"],
    }
    result = runner.run_job(job_data)
    # Current _base_result always uses MockEngine
    assert result.engine_used == "mock"


# ---------------------------------------------------------------------------
# Test 11: RealEnginePolicy allows opencode and hermes
# ---------------------------------------------------------------------------


def test_real_engine_policy_allows_opencode_and_hermes() -> None:
    """RealEnginePolicy authorizes real-engine commands that SafeCommandPolicy denies."""
    real_policy = RealEnginePolicy()
    safe_policy = SafeCommandPolicy()

    # RealEnginePolicy allows real-engine commands
    assert real_policy.is_allowed("opencode run --prompt test")
    assert real_policy.is_allowed("hermes chat -q test")
    assert real_policy.is_allowed("git add .")
    assert real_policy.is_allowed("git commit -m test")
    assert real_policy.is_allowed("git checkout -b feature")
    assert real_policy.is_allowed("git branch feature")

    # RealEnginePolicy also allows the original SafeCommandPolicy prefixes
    assert real_policy.is_allowed("python -m pytest")
    assert real_policy.is_allowed("pytest -q")
    assert real_policy.is_allowed("git status")
    assert real_policy.is_allowed("git diff")
    assert real_policy.is_allowed("git rev-parse HEAD")
    assert real_policy.is_allowed("graphify update")

    # RealEnginePolicy denies dangerous commands
    assert not real_policy.is_allowed("rm -rf /")
    assert not real_policy.is_allowed("git merge main")
    assert not real_policy.is_allowed("git rebase origin/main")
    assert not real_policy.is_allowed("git push origin main")
    assert not real_policy.is_allowed("git pull")
    assert not real_policy.is_allowed("git reset --hard HEAD~1")
    assert not real_policy.is_allowed("powershell Write-Host hi")

    # SafeCommandPolicy does NOT allow opencode or hermes
    assert not safe_policy.is_allowed("opencode run --prompt test")
    assert not safe_policy.is_allowed("hermes chat -q test")
    assert not safe_policy.is_allowed("git add .")
    assert not safe_policy.is_allowed("git commit -m test")

    # But SafeCommandPolicy still allows its original prefixes
    assert safe_policy.is_allowed("python -m pytest")
    assert safe_policy.is_allowed("git status")
    assert safe_policy.is_allowed("git diff")


def test_real_engine_policy_is_allowed_for_engine_delegates() -> None:
    """is_allowed_for_engine delegates to is_allowed."""
    real_policy = RealEnginePolicy()
    assert real_policy.is_allowed_for_engine("opencode run --prompt test") is True
    assert real_policy.is_allowed_for_engine("rm -rf /") is False


def test_safe_policy_denied_consistently() -> None:
    """SafeCommandPolicy consistently denies the denied_prefixes."""
    policy = SafeCommandPolicy()
    assert policy.is_denied("rm -rf /")
    assert policy.is_denied("del important.txt")
    assert policy.is_denied("rmdir /some/dir")
    assert policy.is_denied("git merge main")
    assert policy.is_denied("git push origin")


# ---------------------------------------------------------------------------
# Test 12: JobContract engine_config
# ---------------------------------------------------------------------------


def test_job_contract_engine_config() -> None:
    """JobContract.engine_config_value reads from engine_config with metadata fallback."""
    contract = JobContract.from_mapping({
        "job_id": "test-config",
        "repository_path": ".",
        "task_title": "Config Test",
        "task_prompt": "test",
        "branch_name": "main",
        "engine_name": "hermes",
        "engine_config": {"model": "gpt-5.4-mini"},
        "metadata": {"hermes_model": "fallback-model"},
    })

    # engine_config takes precedence over metadata
    assert contract.engine_config_value("model") == "gpt-5.4-mini"

    # Default value returned for missing keys
    assert contract.engine_config_value("missing", "default") == "default"
    assert contract.engine_config_value("nonexistent") is None

    # Falls back to metadata for keys not in engine_config
    assert contract.engine_config_value("hermes_model") == "fallback-model"


def test_job_contract_engine_config_overrides_metadata() -> None:
    """When a key exists in both engine_config and metadata, engine_config wins."""
    contract = JobContract.from_mapping({
        "job_id": "test-override",
        "repository_path": ".",
        "task_title": "Override Test",
        "task_prompt": "test",
        "branch_name": "main",
        "engine_name": "hermes",
        "engine_config": {"timeout": 900},
        "metadata": {"timeout": 600},
    })
    assert contract.engine_config_value("timeout") == 900


def test_job_contract_engine_config_empty() -> None:
    """When engine_config is empty, falls back entirely to metadata."""
    contract = JobContract.from_mapping({
        "job_id": "test-no-config",
        "repository_path": ".",
        "task_title": "No Config Test",
        "task_prompt": "test",
        "branch_name": "main",
        "engine_name": "hermes",
        "metadata": {"priority": "high"},
    })
    assert contract.engine_config_value("priority") == "high"
    assert contract.engine_config_value("missing") is None


# ---------------------------------------------------------------------------
# Test 13: Auto-Repair — pass-first-time (no repair needed)
# ---------------------------------------------------------------------------


def test_auto_repair_pass_first_time() -> None:
    """When the first run succeeds, auto-repair performs no retries."""
    engine = AutoRepairEngine(max_retries=3)

    call_count = {"count": 0}

    def run_job(job_data: dict) -> JobResult:
        call_count["count"] += 1
        return JobResult(
            job_id=str(job_data.get("job_id", "")),
            status=JobStatus.SUCCESS,
            summary="Passed on first attempt",
            engine_used="mock",
        )

    job_data = {"job_id": "test-pass-first", "task_prompt": "do stuff"}
    result, history = engine.execute_with_repair(job_data, run_job)

    assert result.status == JobStatus.SUCCESS
    assert result.summary == "Passed on first attempt"
    assert len(history) == 1
    assert history[0].attempt == 0
    assert history[0].status == "success"
    assert call_count["count"] == 1  # no retry needed


# ---------------------------------------------------------------------------
# Test 14: Auto-Repair — repair succeeds on retry
# ---------------------------------------------------------------------------


def test_auto_repair_succeeds_on_retry() -> None:
    """When the first attempt fails but the second succeeds, repair works."""
    engine = AutoRepairEngine(max_retries=3)

    call_count = {"count": 0}

    def run_job(job_data: dict) -> JobResult:
        call_count["count"] += 1
        if call_count["count"] == 1:
            return JobResult(
                job_id=str(job_data.get("job_id", "")),
                status=JobStatus.FAILED,
                summary="First attempt failed",
                engine_used="opencode",
                failure_reason="verification_failed",
                verification_results=[
                    {
                        "command": "pytest tests/",
                        "status": "failed",
                        "summary": "AssertionError: expected 2 got 3",
                        "stdout": "",
                        "stderr": "AssertionError: expected 2 got 3",
                        "exit_code": 1,
                        "duration_seconds": 1.0,
                    }
                ],
            )
        # Second call: success
        return JobResult(
            job_id=str(job_data.get("job_id", "")),
            status=JobStatus.SUCCESS,
            summary="Fixed on retry",
            engine_used="opencode",
        )

    job_data = {"job_id": "test-repair-wins", "task_prompt": "fix the tests"}
    result, history = engine.execute_with_repair(job_data, run_job)

    assert result.status == JobStatus.SUCCESS
    assert result.summary == "Fixed on retry"
    assert len(history) == 2
    assert history[0].attempt == 0
    assert history[0].status == "failed"
    assert history[0].strategy == "retry_with_diagnostics"
    assert history[1].attempt == 1
    assert history[1].status == "success"
    assert history[1].strategy == ""  # success entries have no strategy
    # Verify diagnostic was injected
    assert "[Auto-Repair]" in str(job_data.get("task_prompt", ""))


# ---------------------------------------------------------------------------
# Test 15: Auto-Repair — exhausts retries and escalates
# ---------------------------------------------------------------------------


def test_auto_repair_exhausts_retries() -> None:
    """When all repair attempts fail, the engine escalates to terminal failure."""
    engine = AutoRepairEngine(max_retries=2)  # smaller budget for faster test

    call_count = {"count": 0}

    def run_job(job_data: dict) -> JobResult:
        call_count["count"] += 1
        return JobResult(
            job_id=str(job_data.get("job_id", "")),
            status=JobStatus.FAILED,
            summary=f"Attempt {call_count['count']} failed",
            engine_used="opencode",
            failure_reason="verification_failed",
            verification_results=[
                {
                    "command": "pytest tests/",
                    "status": "failed",
                    "summary": "test failure",
                    "stdout": "",
                    "stderr": "FAILED test_something",
                    "exit_code": 1,
                    "duration_seconds": 1.0,
                }
            ],
        )

    job_data = {"job_id": "test-exhausted", "task_prompt": "do the impossible"}
    result, history = engine.execute_with_repair(job_data, run_job)

    # Should be 3 total runs: initial + 2 retries = max_retries + 1
    assert result.status == JobStatus.FAILED
    assert len(history) == 3
    assert call_count["count"] == 3

    # Verify escalation error is annotated
    assert result.error is not None
    assert "Auto-repair exhausted" in (result.error or "")

    # History should show escalation on final entry
    last_entry = history[-1]
    assert last_entry.strategy in ("escalate", "retry_same")
    assert last_entry.attempt == 2


# ---------------------------------------------------------------------------
# Test 16: Auto-Repair — classification logic
# ---------------------------------------------------------------------------


def test_auto_repair_classify_failure() -> None:
    """FailureClass correctly classifies different result scenarios."""
    engine = AutoRepairEngine(max_retries=3)

    # Test failure
    assert (
        engine.classify_failure(
            {
                "status": "failed",
                "verification_results": [
                    {
                        "command": "pytest tests/",
                        "status": "failed",
                        "stderr": "FAILED",
                        "stdout": "",
                    }
                ],
            }
        )
        == FailureClass.TEST_FAILURE
    )

    # Compile error
    assert (
        engine.classify_failure(
            {
                "status": "failed",
                "verification_results": [
                    {
                        "command": "python -c 'import module'",
                        "status": "failed",
                        "stderr": "SyntaxError: invalid syntax",
                        "stdout": "",
                    }
                ],
            }
        )
        == FailureClass.COMPILE_ERROR
    )

    # Timeout
    assert (
        engine.classify_failure({"status": "timed_out", "failure_reason": "timeout"})
        == FailureClass.TIMEOUT
    )

    # Review rejection
    assert (
        engine.classify_failure(
            {"status": "failed", "failure_reason": "review_rejection: needs work"}
        )
        == FailureClass.REVIEW_REJECTION
    )

    # Unknown
    assert (
        engine.classify_failure(
            {"status": "failed", "failure_reason": "something weird happened"}
        )
        == FailureClass.UNKNOWN
    )


# ---------------------------------------------------------------------------
# Test 17: Auto-Repair — blocked/cancelled are never retried
# ---------------------------------------------------------------------------


def test_auto_repair_skips_blocked_and_cancelled() -> None:
    """Blocked and Cancelled statuses exit immediately without retry."""
    engine = AutoRepairEngine(max_retries=3)

    call_count = {"count": 0}

    def run_job(job_data: dict) -> JobResult:
        call_count["count"] += 1
        return JobResult(
            job_id=str(job_data.get("job_id", "")),
            status=JobStatus.BLOCKED,
            summary="Blocked by policy",
            blocked_reason="unsafe_command",
        )

    job_data = {"job_id": "test-blocked", "task_prompt": "rm -rf /"}
    result, history = engine.execute_with_repair(job_data, run_job)

    assert result.status == JobStatus.BLOCKED
    assert len(history) == 1
    assert call_count["count"] == 1  # no retry for blocked
    assert history[0].status == "blocked"
