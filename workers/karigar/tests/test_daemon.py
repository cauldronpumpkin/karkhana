from __future__ import annotations

import json
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from karigar.backend_client import BackendClient
from karigar.circuit_breaker import CircuitBreakerConfig
from karigar.daemon import DaemonConfig, DaemonController, DaemonState
from karigar.models import JobStatus
from karigar.runner import KarigarRunner


# ── helpers ────────────────────────────────────────────────────

class FakeResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self) -> Any:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", "https://example.com/"),
                response=httpx.Response(self.status_code),
            )


def _capturing_post(
    captured: list[dict[str, Any]],
    response: FakeResponse | None = None,
) -> Any:
    def _post(url: str, **kwargs: Any) -> FakeResponse:
        captured.append({"url": url, **kwargs})
        return response or FakeResponse()
    return _post


def _make_client(**kwargs: Any) -> BackendClient:
    defaults = {"api_base_url": "https://example.com", "worker_id": "w1"}
    defaults.update(kwargs)
    return BackendClient(**defaults)


def _make_runner(tmp_path: Path) -> KarigarRunner:
    return KarigarRunner(workspace=tmp_path)


# ======================================================================
# DaemonState
# ======================================================================

class TestDaemonState:
    def test_defaults(self) -> None:
        ds = DaemonState()
        assert ds.worker_id == ""
        assert ds.last_seen_job == ""
        assert ds.jobs_completed_today == 0
        assert ds.jobs_failed_today == 0
        assert ds.total_spend == 0.0
        assert ds.today == datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert ds.last_heartbeat_utc == ""

    def test_to_dict_roundtrip(self) -> None:
        ds = DaemonState(
            worker_id="w1",
            last_seen_job="job-123",
            jobs_completed_today=5,
            jobs_failed_today=2,
            total_spend=0.15,
            today="2026-05-12",
            last_heartbeat_utc="2026-05-12T10:00:00Z",
        )
        d = ds.to_dict()
        assert d["worker_id"] == "w1"
        assert d["jobs_completed_today"] == 5
        assert d["today"] == "2026-05-12"

        restored = DaemonState.from_dict(d)
        assert restored.worker_id == ds.worker_id
        assert restored.jobs_completed_today == ds.jobs_completed_today
        assert restored.total_spend == ds.total_spend

    def test_from_dict_partial(self) -> None:
        ds = DaemonState.from_dict({"worker_id": "w2"})
        assert ds.worker_id == "w2"
        assert ds.jobs_completed_today == 0

    def test_from_dict_empty(self) -> None:
        ds = DaemonState.from_dict({})
        assert ds.worker_id == ""


# ======================================================================
# DaemonConfig
# ======================================================================

class TestDaemonConfig:
    def test_defaults(self) -> None:
        cfg = DaemonConfig()
        assert cfg.poll_interval == 20.0
        assert cfg.heartbeat_interval == 15.0
        assert cfg.run_once is False
        assert cfg.state_dir == Path.home() / ".karigar"

    def test_custom(self) -> None:
        cfg = DaemonConfig(poll_interval=30.0, run_once=True)
        assert cfg.poll_interval == 30.0
        assert cfg.run_once is True


# ======================================================================
# DaemonController initialization + state loading
# ======================================================================

class TestDaemonControllerInit:
    def test_creates_state_dir(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir)
        runner = _make_runner(tmp_path)
        client = _make_client()
        DaemonController(runner=runner, client=client, config=cfg)
        assert state_dir.exists()
        assert state_dir.is_dir()

    def test_loads_existing_state(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".karigar_test"
        state_dir.mkdir(parents=True)
        state_data = {
            "worker_id": "w1",
            "last_seen_job": "j-99",
            "jobs_completed_today": 42,
            "jobs_failed_today": 3,
            "total_spend": 1.23,
            "today": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "last_heartbeat_utc": "",
        }
        (state_dir / "daemon.json").write_text(json.dumps(state_data))

        cfg = DaemonConfig(state_dir=state_dir)
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        assert ctrl.state.jobs_completed_today == 42
        assert ctrl.state.last_seen_job == "j-99"
        assert ctrl.state.total_spend == 1.23

    def test_ignores_corrupt_state_file(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".karigar_test"
        state_dir.mkdir(parents=True)
        (state_dir / "daemon.json").write_text("not valid json {{{")

        cfg = DaemonConfig(state_dir=state_dir)
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        assert ctrl.state.jobs_completed_today == 0  # fresh default

    def test_sets_worker_id_from_client(self, tmp_path: Path) -> None:
        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test")
        runner = _make_runner(tmp_path)
        client = _make_client(worker_id="my-worker-99")
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        assert ctrl.state.worker_id == "my-worker-99"


# ======================================================================
# save / load state
# ======================================================================

class TestDaemonStatePersistence:
    def test_save_state_writes_json(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir)
        runner = _make_runner(tmp_path)
        client = _make_client(worker_id="w1")
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        ctrl.state.last_seen_job = "job-42"
        ctrl.state.jobs_completed_today = 7
        ctrl._save_state()

        state_path = state_dir / "daemon.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert data["worker_id"] == "w1"
        assert data["last_seen_job"] == "job-42"
        assert data["jobs_completed_today"] == 7
        assert "circuit" in data

    def test_save_and_reload_preserves_counters(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir)
        runner = _make_runner(tmp_path)
        client = _make_client(worker_id="w1")

        ctrl1 = DaemonController(runner=runner, client=client, config=cfg)
        ctrl1.state.jobs_completed_today = 10
        ctrl1.circuit.record_claim("job-x")
        ctrl1._save_state()

        ctrl2 = DaemonController(runner=runner, client=client, config=cfg)
        assert ctrl2.state.jobs_completed_today == 10
        assert ctrl2.circuit._jobs_today == 1


# ======================================================================
# day rollover
# ======================================================================

class TestDayRollover:
    def test_resets_daily_counters_on_new_day(self, tmp_path: Path) -> None:
        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test")
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        ctrl.state.today = "2000-01-01"  # old date
        ctrl.state.jobs_completed_today = 99
        ctrl.state.jobs_failed_today = 5

        ctrl._check_day_rollover()

        assert ctrl.state.jobs_completed_today == 0
        assert ctrl.state.jobs_failed_today == 0
        assert ctrl.state.today != "2000-01-01"

    def test_noop_on_same_day(self, tmp_path: Path) -> None:
        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test")
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ctrl.state.today = today
        ctrl.state.jobs_completed_today = 5

        ctrl._check_day_rollover()

        assert ctrl.state.jobs_completed_today == 5


# ======================================================================
# status
# ======================================================================

class TestStatus:
    def test_status_includes_state_and_circuit(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir)
        runner = _make_runner(tmp_path)
        client = _make_client(worker_id="w1")
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        ctrl.state.jobs_completed_today = 3
        ctrl.circuit.record_claim("job-1")

        status = ctrl.status()
        assert status["worker_id"] == "w1"
        assert status["jobs_completed_today"] == 3
        assert status["daemon_running"] is True
        assert status["current_job"] is None
        assert "circuit" in status
        assert status["state_file"] == str(state_dir / "daemon.json")


# ======================================================================
# _run_cycle — integration with mocked HTTP
# ======================================================================

class TestRunCycle:
    def test_run_once_completes_one_cycle(self, tmp_path: Path, monkeypatch) -> None:
        """A full cycle: claim → execute → complete → exit."""
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir, run_once=True, poll_interval=0.1)

        captured: list[dict[str, Any]] = []
        # Claim response
        claim_resp = FakeResponse(json_data={
            "claim": {
                "job_id": "j1",
                "claim_token": "t1",
                "repository_path": str(tmp_path),
                "task_title": "Test",
                "task_prompt": "Do something",
                "branch_name": "main",
                "engine_name": "mock",
                "verification_commands": ["echo ok"],
            }
        })
        mock_post = _capturing_post(captured, response=claim_resp)
        monkeypatch.setattr(httpx, "post", mock_post)

        runner = _make_runner(tmp_path)
        client = _make_client(worker_id="w1")
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        ctrl.run()

        # Should have claimed and completed
        urls = [c["url"] for c in captured]
        assert any("/claim" in u for u in urls)
        assert any("/complete" in u for u in urls) or any("/fail" in u for u in urls)

        # State should be saved
        assert (state_dir / "daemon.json").exists()

    def test_no_job_available_exits_in_run_once(self, tmp_path: Path, monkeypatch) -> None:
        """Empty claim should exit immediately in --run-once."""
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir, run_once=True, poll_interval=0.1)

        captured: list[dict[str, Any]] = []
        empty_claim = FakeResponse(json_data={"claim": {"job_id": ""}})
        mock_post = _capturing_post(captured, response=empty_claim)
        monkeypatch.setattr(httpx, "post", mock_post)

        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        ctrl.run()

        # Should have claimed but NOT completed (no job)
        urls = [c["url"] for c in captured]
        assert any("/claim" in u for u in urls)
        assert not any("/complete" in u for u in urls)
        assert not any("/fail" in u for u in urls)

    def test_claim_failure_retries_then_exits_in_run_once(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Persistent claim failure should retry and eventually exit in --run-once."""
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir, run_once=True, poll_interval=0.1)

        captured: list[dict[str, Any]] = []
        error_resp = FakeResponse(status_code=500)
        mock_post = _capturing_post(captured, response=error_resp)
        monkeypatch.setattr(httpx, "post", mock_post)

        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        # Force shutdown after a brief run to avoid infinite retry
        ctrl._shutdown.set()

        ctrl.run()  # should exit quickly because shutdown is set

        # State should be saved on exit
        assert (state_dir / "daemon.json").exists()


# ======================================================================
# heartbeat
# ======================================================================

class TestHeartbeat:
    def test_heartbeat_sends_correct_payload(self, tmp_path: Path, monkeypatch) -> None:
        captured: list[dict[str, Any]] = []
        claim_resp = FakeResponse(json_data={
            "claim": {
                "job_id": "j1",
                "claim_token": "t1",
                "repository_path": str(tmp_path),
                "task_title": "Test",
                "task_prompt": "Prompt",
                "branch_name": "main",
                "engine_name": "mock",
                "verification_commands": ["echo ok"],
            }
        })
        mock_post = _capturing_post(captured, response=claim_resp)
        monkeypatch.setattr(httpx, "post", mock_post)

        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(
            state_dir=state_dir,
            run_once=True,
            poll_interval=0.1,
            heartbeat_interval=0.1,
        )
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        ctrl.run()

        # At least one heartbeat call should have been made
        urls = [c["url"] for c in captured]
        assert any("/heartbeat" in u for u in urls)

    def test_heartbeat_stops_after_job_completes(self, tmp_path: Path, monkeypatch) -> None:
        """Heartbeat thread should not send heartbeats after job completion."""
        captured: list[dict[str, Any]] = []
        claim_resp = FakeResponse(json_data={
            "claim": {
                "job_id": "j1",
                "claim_token": "t1",
                "repository_path": str(tmp_path),
                "task_title": "Test",
                "task_prompt": "Prompt",
                "branch_name": "main",
                "engine_name": "mock",
                "verification_commands": ["echo ok"],
            }
        })
        mock_post = _capturing_post(captured, response=claim_resp)
        monkeypatch.setattr(httpx, "post", mock_post)

        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir, run_once=True, heartbeat_interval=0.05)
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        ctrl.run()

        # After run_once completes, heartbeat thread should not be running
        assert ctrl._heartbeat_stop.is_set()


# ======================================================================
# circuit breaker integration
# ======================================================================

class TestCircuitBreakerIntegration:
    def test_circuit_breaker_prevents_claim_when_cap_exceeded(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """When daily cap is hit, _run_cycle should return without claiming."""
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir, run_once=True)
        circuit_cfg = CircuitBreakerConfig(max_jobs_per_day=1)

        captured: list[dict[str, Any]] = []
        claim_resp = FakeResponse(json_data={
            "claim": {
                "job_id": "j1",
                "claim_token": "t1",
                "repository_path": str(tmp_path),
                "task_title": "Test",
                "task_prompt": "Prompt",
                "branch_name": "main",
                "engine_name": "mock",
                "verification_commands": ["echo ok"],
            }
        })
        mock_post = _capturing_post(captured, response=claim_resp)
        monkeypatch.setattr(httpx, "post", mock_post)

        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(
            runner=runner, client=client, config=cfg, circuit_config=circuit_cfg
        )

        # First run: should claim and complete
        ctrl.run()
        first_claim_count = sum(1 for c in captured if "/claim" in c["url"])
        assert first_claim_count >= 1

        # Reset captured
        captured.clear()

        # Run again in run_once: breaker should prevent claim
        ctrl2 = DaemonController(
            runner=runner,
            client=client,
            config=cfg,
            circuit_config=circuit_cfg,
        )
        # Restore circuit breaker state from previous run
        ctrl2.circuit = ctrl.circuit  # carry over the state

        ctrl2.run()
        # No new claims because cap is exceeded
        claim_after = sum(1 for c in captured if "/claim" in c["url"])
        assert claim_after == 0


# ======================================================================
# shutdown behavior
# ======================================================================

class TestShutdown:
    def test_save_state_called_on_shutdown(self, tmp_path: Path, monkeypatch) -> None:
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir, run_once=True, poll_interval=0.1)

        captured: list[dict[str, Any]] = []
        claim_resp = FakeResponse(json_data={"claim": {"job_id": ""}})
        mock_post = _capturing_post(captured, response=claim_resp)
        monkeypatch.setattr(httpx, "post", mock_post)

        runner = _make_runner(tmp_path)
        client = _make_client(worker_id="w1")
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        # Set shutdown before running
        ctrl._shutdown.set()
        ctrl.run()

        # State file should exist even though we shut down immediately
        assert (state_dir / "daemon.json").exists()
        data = json.loads((state_dir / "daemon.json").read_text())
        assert data["worker_id"] == "w1"

    def test_handles_signal_without_crashing(self, tmp_path: Path) -> None:
        """Signal handler should set shutdown flag without raising."""
        state_dir = tmp_path / ".karigar_test"
        cfg = DaemonConfig(state_dir=state_dir, run_once=True)
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        # Simulate signal without an actual signal
        ctrl._handle_signal(signal.SIGTERM, None)
        assert ctrl._shutdown.is_set()


# ======================================================================
# _update_state_after_job
# ======================================================================

class TestUpdateStateAfterJob:
    def test_updates_counters_on_success(self, tmp_path: Path) -> None:
        from karigar.models import JobResult

        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test")
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        result = JobResult(
            job_id="job-1",
            status=JobStatus.SUCCESS,
            summary="All good",
            verification_results=[],
        )
        ctrl._update_state_after_job(result)

        assert ctrl.state.last_seen_job == "job-1"
        assert ctrl.state.jobs_completed_today == 1
        assert ctrl.state.jobs_failed_today == 0

    def test_updates_counters_on_failure(self, tmp_path: Path) -> None:
        from karigar.models import JobResult

        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test")
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        result = JobResult(
            job_id="job-2",
            status=JobStatus.FAILED,
            summary="Boom",
            verification_results=[],
        )
        ctrl._update_state_after_job(result)

        assert ctrl.state.last_seen_job == "job-2"
        assert ctrl.state.jobs_completed_today == 1
        assert ctrl.state.jobs_failed_today == 1

    def test_increments_total_spend(self, tmp_path: Path) -> None:
        from karigar.models import JobResult

        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test")
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        result = JobResult(
            job_id="job-3",
            status=JobStatus.SUCCESS,
            summary="Done",
            verification_results=[{"summary": "test passed"}],
        )
        ctrl._update_state_after_job(result)

        assert ctrl.state.total_spend > 0.0


# ======================================================================
# _claim_with_retry
# ======================================================================

class TestClaimWithRetry:
    def test_retries_on_failure(self, tmp_path: Path, monkeypatch) -> None:
        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test", poll_interval=0.05)
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)

        call_count = {"count": 0}

        def flaky_claim(self_cb, capabilities=None) -> dict:
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise httpx.HTTPStatusError(
                    "error",
                    request=httpx.Request("POST", "https://x.com/"),
                    response=httpx.Response(500),
                )
            return {"job_id": "", "claim_token": ""}

        monkeypatch.setattr(
            type(ctrl.client), "claim_job", flaky_claim
        )

        result = ctrl._claim_with_retry()
        # Should have retried 3 times and succeeded on the 3rd
        assert result is not None
        assert call_count["count"] >= 3

    def test_returns_none_on_shutdown(self, tmp_path: Path) -> None:
        cfg = DaemonConfig(state_dir=tmp_path / ".karigar_test", poll_interval=0.05)
        runner = _make_runner(tmp_path)
        client = _make_client()
        ctrl = DaemonController(runner=runner, client=client, config=cfg)
        ctrl._shutdown.set()

        result = ctrl._claim_with_retry()
        assert result is None
