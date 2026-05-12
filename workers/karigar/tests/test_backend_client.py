from __future__ import annotations

import json
import platform
from typing import Any

import httpx
import pytest

from karigar.backend_client import BackendClient


# ── helpers ──────────────────────────────────────────────

def _make_client(**kwargs: Any) -> BackendClient:
    return BackendClient(
        api_base_url="https://example.com",
        worker_id="w1",
        **kwargs,
    )


class FakeResponse:
    """Minimal httpx.Response stand-in for monkeypatching."""

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
    """Return a callable that captures the kwargs of httpx.post and returns a controlled response."""

    def _post(url: str, **kwargs: Any) -> FakeResponse:
        captured.append({"url": url, **kwargs})
        return response or FakeResponse()

    return _post


# ── claim_job ────────────────────────────────────────────

def test_claim_job_returns_claim_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_post = _capturing_post(
        captured,
        response=FakeResponse(json_data={"claim": {"job_id": "j1", "claim_token": "t1"}}),
    )
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    claim = client.claim_job(capabilities=["python"])

    assert claim == {"job_id": "j1", "claim_token": "t1"}
    assert len(captured) == 1
    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["worker_id"] == "w1"
    assert body["capabilities"] == ["python"]


def test_claim_job_no_claim_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_post = _capturing_post(
        [],
        response=FakeResponse(json_data={"claim": {}}),
    )
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    with pytest.raises(ValueError, match="No claim returned"):
        client.claim_job()


def test_claim_job_empty_claim_missing_job_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_post = _capturing_post(
        [],
        response=FakeResponse(json_data={"claim": {"not_job_id": "x"}}),
    )
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    with pytest.raises(ValueError, match="No claim returned"):
        client.claim_job()


# ── complete_job ─────────────────────────────────────────

def test_complete_job_sends_correct_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_post = _capturing_post(captured)
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    result_payload = {"status": "success", "summary": "ok"}
    client.complete_job(
        job_id="j1",
        claim_token="t1",
        result=result_payload,
        logs="some logs",
        engine="opencode",
        model="gpt-4",
        agent_name="hermes",
        command="pytest",
        branch_name="main",
    )

    assert len(captured) == 1
    assert captured[0]["url"] == "https://example.com/api/worker/jobs/j1/complete"
    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["worker_id"] == "w1"
    assert body["claim_token"] == "t1"
    assert body["result"] == result_payload
    assert body["logs"] == "some logs"
    assert body["engine"] == "opencode"
    assert body["model"] == "gpt-4"
    assert body["agent_name"] == "hermes"
    assert body["command"] == "pytest"
    assert body["branch_name"] == "main"


def test_complete_job_omits_optional_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_post = _capturing_post(captured)
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    client.complete_job(
        job_id="j1",
        claim_token="t1",
        result={"status": "ok"},
    )

    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert "engine" not in body
    assert "model" not in body
    assert "agent_name" not in body
    assert "command" not in body
    assert "branch_name" not in body


# ── fail_job ─────────────────────────────────────────────

def test_fail_job_sends_correct_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_post = _capturing_post(captured)
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    client.fail_job(
        job_id="j2",
        claim_token="t2",
        error="something broke",
        retryable=False,
        logs="error logs",
    )

    assert len(captured) == 1
    assert captured[0]["url"] == "https://example.com/api/worker/jobs/j2/fail"
    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["worker_id"] == "w1"
    assert body["claim_token"] == "t2"
    assert body["error"] == "something broke"
    assert body["retryable"] is False
    assert body["logs"] == "error logs"


def test_fail_job_defaults_retryable_true(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_post = _capturing_post(captured)
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    client.fail_job(job_id="j2", claim_token="t2", error="oops")

    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["retryable"] is True


# ── heartbeat_job ────────────────────────────────────────

def test_heartbeat_job_sends_correct_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_post = _capturing_post(captured)
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    client.heartbeat_job(job_id="j3", claim_token="t3", logs="ping")

    assert len(captured) == 1
    assert captured[0]["url"] == "https://example.com/api/worker/jobs/j3/heartbeat"
    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["worker_id"] == "w1"
    assert body["claim_token"] == "t3"
    assert body["logs"] == "ping"


# ── headers / auth ───────────────────────────────────────

def test_headers_include_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    valid_response = FakeResponse(json_data={"claim": {"job_id": "j1", "claim_token": "t1"}})
    monkeypatch.setattr(httpx, "post", _capturing_post(captured, response=valid_response))

    client = _make_client(worker_token="secret-token")
    client.claim_job()

    headers = captured[0].get("headers", {})
    assert headers.get("Authorization") == "Bearer secret-token"
    assert headers.get("Content-Type") == "application/json"


def test_headers_no_auth_when_token_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    valid_response = FakeResponse(json_data={"claim": {"job_id": "j1", "claim_token": "t1"}})
    monkeypatch.setattr(httpx, "post", _capturing_post(captured, response=valid_response))

    client = _make_client(worker_token="")
    client.claim_job()

    headers = captured[0].get("headers", {})
    assert "Authorization" not in headers


# ── register_worker ──────────────────────────────────────

def test_register_worker_includes_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "post", _capturing_post(captured))

    client = _make_client()
    client.register_worker(machine_name="my-machine", display_name="My Worker")

    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["machine_name"] == "my-machine"
    assert body["platform"] == platform.system().lower()
    assert body["engine"] == "opencode"
    assert body["display_name"] == "My Worker"
    assert "capabilities" not in body
    # registration does NOT use auth headers
    headers = captured[0].get("headers", {})
    assert "Authorization" not in headers


def test_register_worker_with_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "post", _capturing_post(captured))

    client = _make_client()
    client.register_worker(capabilities=["python", "node"])

    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["capabilities"] == ["python", "node"]


def test_register_worker_falls_back_to_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "post", _capturing_post(captured))

    client = _make_client()
    client.register_worker()

    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    # should be platform.node() or the fallback
    assert body["machine_name"] is not None
    assert len(body["machine_name"]) > 0


# ── post_event ───────────────────────────────────────────

def test_post_event_sends_correct_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "post", _capturing_post(captured))

    client = _make_client()
    client.post_event("job.started", {"job_id": "j1"})

    assert captured[0]["url"] == "https://example.com/api/local-workers/w1/events"
    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["type"] == "job.started"
    assert body["payload"] == {"job_id": "j1"}


def test_post_event_defaults_empty_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "post", _capturing_post(captured))

    client = _make_client()
    client.post_event("heartbeat")

    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["payload"] == {}


# ── HTTP error propagation ───────────────────────────────

def test_http_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_post = _capturing_post([], response=FakeResponse(status_code=500))
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    with pytest.raises(httpx.HTTPStatusError):
        client.claim_job()


# ── report_result ─────────────────────────────────────────

def test_report_result_delegates_to_complete_job(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_post = _capturing_post(captured)
    monkeypatch.setattr(httpx, "post", mock_post)

    client = _make_client()
    client.report_result(
        job_id="j1",
        claim_token="t1",
        result={"status": "done"},
        logs="all good",
        engine="hermes",
        model="gpt-5.5",
    )

    assert len(captured) == 1
    assert captured[0]["url"] == "https://example.com/api/worker/jobs/j1/complete"


# ── get_job_status ────────────────────────────────────────

def test_get_job_status_returns_status(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    mock_get = _capturing_post(
        captured,
        response=FakeResponse(json_data={"job_id": "j1", "status": "running"}),
    )
    monkeypatch.setattr(httpx, "get", mock_get)

    client = _make_client()
    status = client.get_job_status("j1")

    assert status == {"job_id": "j1", "status": "running"}
    assert captured[0]["url"] == "https://example.com/api/worker/jobs/j1"


def test_get_job_status_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_get = _capturing_post([], response=FakeResponse(status_code=404))
    monkeypatch.setattr(httpx, "get", mock_get)

    client = _make_client()
    with pytest.raises(httpx.HTTPStatusError):
        client.get_job_status("nonexistent")


# ── create_ledger_entry ───────────────────────────────────

def test_create_ledger_entry_sends_correct_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "post", _capturing_post(captured))

    client = _make_client()
    client.create_ledger_entry(
        run_id="run-1",
        title="Job completed",
        status="completed",
        stage="execution",
        body="# Ledger body",
    )

    assert captured[0]["url"] == "https://example.com/api/ledgers/run-1"
    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["title"] == "Job completed"
    assert body["status"] == "completed"
    assert body["stage"] == "execution"
    assert body["body"] == "# Ledger body"


def test_create_ledger_entry_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "post", _capturing_post(captured))

    client = _make_client()
    client.create_ledger_entry(run_id="run-2", title="Minimal")

    body = json.loads(captured[0]["json"]) if isinstance(captured[0].get("json"), str) else captured[0]["json"]
    assert body["status"] == "active"
    assert body["stage"] == "execution"
    assert body["body"] == ""


# ── _build_ledger_body ────────────────────────────────────

def test_build_ledger_body_includes_status_and_engine() -> None:
    from karigar.backend_client import _build_ledger_body

    result = {
        "status": "success",
        "summary": "All tests passed",
        "engine_used": "opencode",
        "changed_files": ["src/main.py"],
        "verification_results": [
            {"status": "passed", "command": "pytest"},
        ],
    }
    body = _build_ledger_body(result, "job-123")
    assert "job-123" in body
    assert "success" in body
    assert "opencode" in body
    assert "src/main.py" in body
    assert "pytest" in body


def test_build_ledger_body_no_engine() -> None:
    from karigar.backend_client import _build_ledger_body

    result = {"status": "failed", "summary": "Boom"}
    body = _build_ledger_body(result, "j1")
    assert "failed" in body
    assert "mock" in body
