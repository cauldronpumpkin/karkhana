"""End-to-end integration: claim → engine.run() → report_result.

Uses the mock engine with a fake HTTP backend so no network is needed.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
import pytest

from karigar.backend_client import BackendClient
from karigar.models import JobContract, JobResult, JobStatus
from karigar.runner import KarigarRunner


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


def _capture_get(response: FakeResponse | None = None) -> Any:
    captured: list[dict[str, Any]] = []
    def _get(url: str, **kwargs: Any) -> FakeResponse:
        captured.append({"url": url, **kwargs})
        return response or FakeResponse()
    _get.captured = captured  # type: ignore[attr-defined]
    return _get


def _capture_post(response: FakeResponse | None = None) -> Any:
    captured: list[dict[str, Any]] = []
    def _post(url: str, **kwargs: Any) -> FakeResponse:
        captured.append({"url": url, **kwargs})
        return response or FakeResponse()
    _post.captured = captured  # type: ignore[attr-defined]
    return _post


# ── End-to-end: claim → mock run → report ───────────────

def test_e2e_claim_run_report(monkeypatch: pytest.MonkeyPatch) -> None:
    """Full cycle: claim a job, run with mock engine, report result."""
    mock_get = _capture_get()
    mock_post = _capture_post()
    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr(httpx, "post", mock_post)

    client = BackendClient(
        api_base_url="https://api.karkhana.one",
        worker_id="test-worker",
    )

    # Step 1: Claim — inject claim response
    claim_response = FakeResponse(json_data={
        "claim": {
            "job_id": "e2e-job-1",
            "claim_token": "e2e-token",
            "command": "echo hello",
            "repo_root": "/tmp/karkhana-e2e",
        }
    })
    monkeypatch.setattr(httpx, "post", _capture_post(response=claim_response))
    claim = client.claim_job()

    assert claim["job_id"] == "e2e-job-1"
    assert claim["claim_token"] == "e2e-token"

    # Step 2: Run with mock engine
    runner = KarigarRunner(workspace=Path("/tmp/karkhana-e2e"))
    contract = JobContract(
        job_id=claim["job_id"],
        repository_path=claim.get("repo_root", "/tmp/karkhana-e2e"),
        task_title="E2E test job",
        task_prompt="Run echo hello",
        branch_name="main",
        engine_name="mock",
        command=claim.get("command", "echo hello"),
    )
    result = runner.run_job(asdict(contract))

    assert result.status == JobStatus.SUCCESS

    # Step 3: Report result
    complete_response = FakeResponse(json_data={"status": "ok"})
    monkeypatch.setattr(httpx, "post", _capture_post(response=complete_response))
    resp = client.report_result(
        job_id=claim["job_id"],
        claim_token=claim["claim_token"],
        result={"status": result.status, "summary": result.summary},
        logs=result.stdout or "",
        engine="mock",
    )

    assert resp["status"] == "ok"


def test_e2e_claim_fail_report(monkeypatch: pytest.MonkeyPatch) -> None:
    """Claim a job, fail the run, report failure."""
    mock_post = _capture_post()
    monkeypatch.setattr(httpx, "post", mock_post)

    client = BackendClient(
        api_base_url="https://api.karkhana.one",
        worker_id="test-worker",
    )

    # Claim with empty result — simulate no job available
    no_claim = _capture_post(response=FakeResponse(json_data={"claim": {}}))
    monkeypatch.setattr(httpx, "post", no_claim)

    with pytest.raises(ValueError, match="No claim returned"):
        client.claim_job()
