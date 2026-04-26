from __future__ import annotations

import hashlib
import json
import secrets
from datetime import timedelta
from typing import Any

from backend.app.config import settings
from backend.app.repository import (
    LocalWorker,
    WorkerConnectionRequest,
    WorkerCredentialLease,
    WorkerEvent,
    get_repository,
    utcnow,
)
from backend.app.services.project_twin import ProjectTwinService, to_jsonable


DEFAULT_CAPABILITIES = [
    "repo_index",
    "architecture_dossier",
    "gap_analysis",
    "build_task_plan",
    "agent_branch_work",
    "test_verify",
    "sync_remote_state",
]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LocalWorkerService:
    async def register_request(self, data: dict[str, Any]) -> dict[str, Any]:
        pairing_token = secrets.token_urlsafe(24)
        requested_config = data.get("config") or {}
        requested_config["_pairing_token_hash"] = hash_token(pairing_token)
        request = WorkerConnectionRequest(
            display_name=(data.get("display_name") or data.get("machine_name") or "Local worker").strip(),
            machine_name=(data.get("machine_name") or "unknown").strip(),
            platform=(data.get("platform") or "unknown").strip(),
            engine=(data.get("engine") or "openclaude").strip(),
            capabilities=data.get("capabilities") or DEFAULT_CAPABILITIES,
            requested_config=requested_config,
            tenant_id=(data.get("tenant_id") or "").strip() or None,
        )
        await get_repository().save_worker_connection_request(request)
        return {"request": self._public_request(request), "pairing_token": pairing_token}

    async def get_registration(self, request_id: str, pairing_token: str = "") -> dict[str, Any]:
        request = await self._request_or_404(request_id)
        worker = await get_repository().get_local_worker(request.worker_id) if request.worker_id else None
        lease = await get_repository().get_worker_credential_lease(worker.id) if worker else None
        public_lease = self._public_lease(lease)
        if public_lease and self._pairing_token_matches(request, pairing_token):
            api_token = request.requested_config.pop("_api_token_once", None)
            if api_token:
                public_lease["api_token"] = api_token
                await get_repository().save_worker_connection_request(request)
        return {
            "request": self._public_request(request),
            "worker": self._public_worker(worker) if worker else None,
            "credentials": public_lease if request.status == "approved" and lease else None,
        }

    async def dashboard(self) -> dict[str, Any]:
        repo = get_repository()
        workers = await repo.list_local_workers()
        requests = await repo.list_worker_connection_requests()
        events = await repo.list_worker_events()
        jobs = await repo.list_work_items()
        return {
            "workers": [self._public_worker(worker) for worker in workers],
            "requests": [self._public_request(item) for item in requests],
            "events": [to_jsonable(event) for event in events[:50]],
            "jobs": [to_jsonable(job) for job in jobs[:30]],
            "sqs": {
                "commands_configured": bool(settings.worker_command_queue_url),
                "events_configured": bool(settings.worker_event_queue_url),
                "region": settings.worker_sqs_region,
            },
        }

    async def list_requests(self) -> dict[str, Any]:
        return {"requests": [self._public_request(item) for item in await get_repository().list_worker_connection_requests()]}

    async def approve_request(self, request_id: str) -> dict[str, Any]:
        request = await self._request_or_404(request_id)
        if request.status == "approved" and request.worker_id:
            worker = await get_repository().get_local_worker(request.worker_id)
            lease = await get_repository().get_worker_credential_lease(request.worker_id)
            return {"request": self._public_request(request), "worker": self._public_worker(worker), "credentials": self._public_lease(lease)}
        if request.status != "pending":
            raise ValueError(f"Request is already {request.status}")

        token = secrets.token_urlsafe(32)
        worker = LocalWorker(
            display_name=request.display_name,
            machine_name=request.machine_name,
            platform=request.platform,
            engine=request.engine,
            capabilities=request.capabilities,
            config={**request.requested_config, "autonomy": request.requested_config.get("autonomy", "branch_pr")},
            api_token_hash=hash_token(token),
        )
        await get_repository().save_local_worker(worker)
        lease = await self._issue_credentials(worker, token)
        request.status = "approved"
        request.worker_id = worker.id
        request.requested_config["_api_token_once"] = getattr(lease, "api_token", "")
        await get_repository().save_worker_connection_request(request)
        return {"request": self._public_request(request), "worker": self._public_worker(worker), "credentials": self._public_lease(lease)}

    async def deny_request(self, request_id: str, reason: str = "") -> dict[str, Any]:
        request = await self._request_or_404(request_id)
        request.status = "denied"
        request.decision_reason = reason or "Denied in Local Workers"
        await get_repository().save_worker_connection_request(request)
        return {"request": self._public_request(request)}

    async def revoke_worker(self, worker_id: str) -> dict[str, Any]:
        worker = await self._worker_or_404(worker_id)
        worker.status = "revoked"
        worker.api_token_hash = None
        await get_repository().save_local_worker(worker)
        return {"worker": self._public_worker(worker)}

    async def rotate_credentials(self, worker_id: str) -> dict[str, Any]:
        worker = await self._worker_or_404(worker_id)
        if worker.status != "approved":
            raise ValueError("Only approved workers can rotate credentials")
        token = secrets.token_urlsafe(32)
        worker.api_token_hash = hash_token(token)
        await get_repository().save_local_worker(worker)
        lease = await self._issue_credentials(worker, token)
        return {"worker": self._public_worker(worker), "credentials": self._public_lease(lease)}

    async def verify_worker_token(self, worker_id: str, token: str) -> LocalWorker:
        worker = await self._worker_or_404(worker_id)
        if worker.status != "approved" or not worker.api_token_hash or hash_token(token) != worker.api_token_hash:
            raise PermissionError("Invalid worker credentials")
        lease = await get_repository().get_worker_credential_lease(worker_id)
        if lease and lease.expires_at < utcnow():
            raise PermissionError("Worker credentials expired")
        worker.last_seen_at = utcnow()
        await get_repository().save_local_worker(worker)
        return worker

    async def record_event(self, worker_id: str, event_type: str, payload: dict[str, Any], work_item_id: str | None = None) -> WorkerEvent:
        event = WorkerEvent(worker_id=worker_id, event_type=event_type, payload=payload, work_item_id=work_item_id)
        await get_repository().add_worker_event(event)
        return event

    async def process_worker_event(self, worker_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        await self.record_event(worker_id, event_type, payload, payload.get("work_item_id"))
        project_service = ProjectTwinService()
        if event_type == "heartbeat":
            await self._heartbeat_worker(worker_id)
            if payload.get("work_item_id") and payload.get("claim_token"):
                return {"job": await project_service.heartbeat_job(payload["work_item_id"], payload["claim_token"], worker_id, payload.get("logs", ""))}
            return {"ok": True}
        if event_type == "job_completed":
            return {"job": await project_service.complete_job(payload["work_item_id"], payload["claim_token"], worker_id, payload.get("result") or {}, payload.get("logs", ""))}
        if event_type == "job_failed":
            return {"job": await project_service.fail_job(payload["work_item_id"], payload["claim_token"], worker_id, payload.get("error") or "Worker failed", bool(payload.get("retryable", True)), payload.get("logs", ""))}
        return {"ok": True}

    async def process_sqs_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        processed = 0
        for record in records:
            body = json.loads(record.get("body") or "{}")
            await self.process_worker_event(
                body.get("worker_id") or "unknown",
                body.get("type") or body.get("event_type") or "unknown",
                body.get("payload") or body,
            )
            processed += 1
        return {"processed": processed}

    async def _heartbeat_worker(self, worker_id: str) -> None:
        worker = await get_repository().get_local_worker(worker_id)
        if worker:
            worker.last_seen_at = utcnow()
            await get_repository().save_local_worker(worker)

    async def _issue_credentials(self, worker: LocalWorker, api_token: str) -> WorkerCredentialLease:
        expires_at = utcnow() + timedelta(seconds=settings.worker_credential_ttl_seconds)
        aws_creds = self._assume_worker_role(worker, expires_at)
        lease = WorkerCredentialLease(
            worker_id=worker.id,
            api_token_hash=worker.api_token_hash or hash_token(api_token),
            access_key_id=aws_creds["access_key_id"],
            secret_access_key=aws_creds["secret_access_key"],
            session_token=aws_creds["session_token"],
            expires_at=expires_at,
            command_queue_url=settings.worker_command_queue_url,
            event_queue_url=settings.worker_event_queue_url,
            region=settings.worker_sqs_region,
        )
        await get_repository().save_worker_credential_lease(lease)
        public_lease = WorkerCredentialLease(
            id=lease.id,
            worker_id=lease.worker_id,
            api_token_hash=lease.api_token_hash,
            access_key_id=lease.access_key_id,
            secret_access_key=lease.secret_access_key,
            session_token=lease.session_token,
            expires_at=lease.expires_at,
            command_queue_url=lease.command_queue_url,
            event_queue_url=lease.event_queue_url,
            region=lease.region,
            created_at=lease.created_at,
        )
        public_lease.api_token = api_token  # type: ignore[attr-defined]
        return public_lease

    def _assume_worker_role(self, worker: LocalWorker, expires_at) -> dict[str, str]:
        if not settings.worker_client_role_arn:
            return {
                "access_key_id": "local-dev-access-key",
                "secret_access_key": "local-dev-secret-key",
                "session_token": f"local-dev-session:{worker.id}:{int(expires_at.timestamp())}",
            }
        import boto3

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
                    "Resource": "*",
                },
                {
                    "Effect": "Allow",
                    "Action": ["sqs:SendMessage", "sqs:GetQueueAttributes"],
                    "Resource": "*",
                },
            ],
        }
        response = boto3.client("sts", region_name=settings.worker_sqs_region).assume_role(
            RoleArn=settings.worker_client_role_arn,
            RoleSessionName=f"idearefinery-worker-{worker.id[:8]}",
            DurationSeconds=max(900, min(settings.worker_credential_ttl_seconds, 43200)),
            Policy=json.dumps(policy),
        )
        credentials = response["Credentials"]
        return {
            "access_key_id": credentials["AccessKeyId"],
            "secret_access_key": credentials["SecretAccessKey"],
            "session_token": credentials["SessionToken"],
        }

    async def _request_or_404(self, request_id: str) -> WorkerConnectionRequest:
        request = await get_repository().get_worker_connection_request(request_id)
        if not request:
            raise ValueError("Worker connection request not found")
        return request

    async def _worker_or_404(self, worker_id: str) -> LocalWorker:
        worker = await get_repository().get_local_worker(worker_id)
        if not worker:
            raise ValueError("Local worker not found")
        return worker

    def _public_worker(self, worker: LocalWorker | None) -> dict[str, Any] | None:
        if not worker:
            return None
        data = to_jsonable(worker)
        data.pop("api_token_hash", None)
        return data

    def _public_request(self, request: WorkerConnectionRequest) -> dict[str, Any]:
        data = to_jsonable(request)
        config = dict(data.get("requested_config") or {})
        for key in list(config):
            if key.startswith("_"):
                config.pop(key, None)
        data["requested_config"] = config
        return data

    def _public_lease(self, lease: WorkerCredentialLease | None) -> dict[str, Any] | None:
        if not lease:
            return None
        data = to_jsonable(lease)
        data["api_token"] = getattr(lease, "api_token", None)
        data.pop("api_token_hash", None)
        return data

    def _pairing_token_matches(self, request: WorkerConnectionRequest, pairing_token: str) -> bool:
        expected = request.requested_config.get("_pairing_token_hash")
        return bool(expected and pairing_token and hash_token(pairing_token) == expected)
