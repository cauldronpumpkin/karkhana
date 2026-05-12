from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class BackendClient:
    """HTTP client for the Karkhana worker API."""

    api_base_url: str
    worker_id: str
    worker_token: str = ""
    timeout: float = 30.0

    # ── Headers ──────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.worker_token:
            headers["Authorization"] = f"Bearer {self.worker_token}"
        return headers

    # ── Claim a job ─────────────────────────────────────────

    def claim_job(self, capabilities: list[str] | None = None) -> dict[str, Any]:
        """Claim a pending job. Returns the claim dict with job_id, claim_token, task details."""
        body: dict[str, Any] = {"worker_id": self.worker_id}
        if capabilities:
            body["capabilities"] = capabilities
        response = httpx.post(
            f"{self.api_base_url}/api/worker/claim",
            json=body,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        claim = data.get("claim", {})
        if not claim or not claim.get("job_id"):
            raise ValueError(f"No claim returned from backend: {data}")
        return claim

    # ── Report job completion ───────────────────────────────

    def complete_job(
        self,
        job_id: str,
        claim_token: str,
        result: dict[str, Any],
        logs: str = "",
        engine: str | None = None,
        model: str | None = None,
        agent_name: str | None = None,
        command: str | None = None,
        branch_name: str | None = None,
    ) -> dict[str, Any]:
        """Report a job as completed."""
        body: dict[str, Any] = {
            "worker_id": self.worker_id,
            "claim_token": claim_token,
            "result": result,
            "logs": logs,
        }
        if engine:
            body["engine"] = engine
        if model:
            body["model"] = model
        if agent_name:
            body["agent_name"] = agent_name
        if command:
            body["command"] = command
        if branch_name:
            body["branch_name"] = branch_name
        response = httpx.post(
            f"{self.api_base_url}/api/worker/jobs/{job_id}/complete",
            json=body,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ── Report job failure ──────────────────────────────────

    def fail_job(
        self,
        job_id: str,
        claim_token: str,
        error: str,
        retryable: bool = True,
        logs: str = "",
    ) -> dict[str, Any]:
        """Report a job as failed."""
        body = {
            "worker_id": self.worker_id,
            "claim_token": claim_token,
            "error": error,
            "retryable": retryable,
            "logs": logs,
        }
        response = httpx.post(
            f"{self.api_base_url}/api/worker/jobs/{job_id}/fail",
            json=body,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ── Send heartbeat ──────────────────────────────────────

    def heartbeat_job(
        self,
        job_id: str,
        claim_token: str,
        logs: str = "",
    ) -> dict[str, Any]:
        """Send a heartbeat to keep the job claim alive."""
        body = {
            "worker_id": self.worker_id,
            "claim_token": claim_token,
            "logs": logs,
        }
        response = httpx.post(
            f"{self.api_base_url}/api/worker/jobs/{job_id}/heartbeat",
            json=body,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ── Register worker ─────────────────────────────────────

    def register_worker(
        self,
        machine_name: str | None = None,
        engine: str = "opencode",
        capabilities: list[str] | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Register this worker with the backend. Returns registration details including worker_id and token."""
        body = {
            "machine_name": machine_name or platform.node() or "karigar-worker",
            "platform": platform.system().lower(),
            "engine": engine,
            "display_name": display_name,
        }
        if capabilities:
            body["capabilities"] = capabilities
        response = httpx.post(
            f"{self.api_base_url}/api/local-workers/register",
            json=body,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ── Post a worker event ─────────────────────────────────

    def post_event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Post a worker event to the backend."""
        body = {"type": event_type, "payload": payload or {}}
        response = httpx.post(
            f"{self.api_base_url}/api/local-workers/{self.worker_id}/events",
            json=body,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ── Emit run-scoped event (WebSocket broadcast) ──────────

    def emit_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a run-scoped event to be broadcast to WebSocket subscribers.

        Posts to POST /api/ws/emit with run_id, event_type, and optional payload.
        Uses worker token (Authorization header) and X-Worker-ID header for auth.
        """
        headers = self._headers()
        headers["X-Worker-ID"] = self.worker_id
        body = {
            "run_id": run_id,
            "event_type": event_type,
            "payload": payload or {},
        }
        response = httpx.post(
            f"{self.api_base_url}/api/ws/emit",
            json=body,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


    # ── Report result (alias for complete_job) ───────────────

    def report_result(
        self,
        job_id: str,
        claim_token: str,
        result: dict[str, Any],
        logs: str = "",
        engine: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        """Report job result (convenience alias for complete_job)."""
        return self.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            result=result,
            logs=logs,
            engine=engine,
            model=model,
        )

    # ── Get job status ───────────────────────────────────────

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the current status of a job from the backend."""
        response = httpx.get(
            f"{self.api_base_url}/api/worker/jobs/{job_id}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ── Factory Run Ledger ────────────────────────────────────

    def create_ledger_entry(
        self,
        run_id: str,
        title: str,
        status: str = "active",
        stage: str = "execution",
        body: str = "",
    ) -> dict[str, Any]:
        """Create a ledger entry for a factory run."""
        payload = {
            "title": title,
            "status": status,
            "stage": stage,
            "body": body,
        }
        response = httpx.post(
            f"{self.api_base_url}/api/ledgers/{run_id}",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


__all__ = ["BackendClient"]


def _build_ledger_body(result: dict[str, Any], job_id: str) -> str:
    """Build a markdown ledger body from job results."""
    status = result.get("status", "unknown")
    summary = result.get("summary", "")
    engine = result.get("engine_used", "")
    changed = result.get("changed_files", [])
    verification = result.get("verification_results", [])

    lines = [
        f"# Job {job_id}",
        "",
        f"**Status:** {status}",
        f"**Engine:** {engine or 'mock'}",
        f"**Summary:** {summary}",
        "",
    ]
    if changed:
        lines.append("## Changed Files")
        for f in changed:
            lines.append(f"- `{f}`")
        lines.append("")

    if verification:
        lines.append("## Verification Results")
        for v in verification:
            v_status = v.get("status", "?")
            v_cmd = v.get("command", "?")
            lines.append(f"- **{v_status}** `{v_cmd}`")
        lines.append("")

    return "\n".join(lines)
