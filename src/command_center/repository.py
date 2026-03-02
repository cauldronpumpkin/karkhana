"""SQLite repository for Command Center data."""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any

from src.command_center.db import get_connection, init_db
from src.command_center.models import JobStatus


JSON_COLUMNS = {
    "payload_json",
    "meta_json",
    "prompt_json",
    "response_json",
    "content_json",
    "value_json",
    "override_json",
    "metadata_json",
    "launch_override_json",
}
BOOL_COLUMNS = {"approval_required", "required", "blocking"}


def _row_to_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in JSON_COLUMNS:
        if key in item and isinstance(item[key], str):
            try:
                item[key] = json.loads(item[key] or "{}")
            except json.JSONDecodeError:
                item[key] = {}
    for key in BOOL_COLUMNS:
        if key in item:
            item[key] = bool(item[key])
    return item


class CommandCenterRepository:
    """Repository providing CRUD for jobs, events, logs, artifacts, decisions, and agent messages."""

    def __init__(self) -> None:
        init_db()
        self._lock = threading.Lock()

    def create_job(self, idea: str, approval_required: bool = False, label: str | None = None) -> dict[str, Any]:
        now = time.time()
        job_id = uuid.uuid4().hex[:12]
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, idea, status, approval_required, created_at, progress_percent, label
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, idea, JobStatus.QUEUED.value, int(approval_required), now, 0.0, label),
            )
            conn.commit()
        return self.get_job(job_id) or {}

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def list_jobs(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock, get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def list_jobs_by_status(self, statuses: list[str]) -> list[dict[str, Any]]:
        if not statuses:
            return []
        placeholders = ",".join(["?"] * len(statuses))
        with self._lock, get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE status IN ({placeholders}) ORDER BY created_at ASC",
                tuple(statuses),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def update_job_status(
        self,
        job_id: str,
        status: str,
        *,
        error_message: str | None = None,
        current_stage: str | None = None,
        progress_percent: float | None = None,
    ) -> None:
        now = time.time()
        fields: list[str] = ["status = ?"]
        values: list[Any] = [status]
        if error_message is not None:
            fields.append("error_message = ?")
            values.append(error_message)
        if current_stage is not None:
            fields.append("current_stage = ?")
            values.append(current_stage)
        if progress_percent is not None:
            fields.append("progress_percent = ?")
            values.append(progress_percent)
        if status == JobStatus.RUNNING.value:
            fields.append("started_at = COALESCE(started_at, ?)")
            values.append(now)
        if status == JobStatus.COMPLETED.value:
            fields.append("finished_at = ?")
            values.append(now)
            fields.append("progress_percent = 100.0")
        if status == JobStatus.STOPPED.value:
            fields.append("stopped_at = ?")
            values.append(now)
        values.append(job_id)
        with self._lock, get_connection() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", tuple(values))
            conn.commit()

    def update_job_stage(self, job_id: str, stage: str, progress_percent: float | None = None) -> None:
        fields = ["current_stage = ?"]
        values: list[Any] = [stage]
        if progress_percent is not None:
            fields.append("progress_percent = ?")
            values.append(progress_percent)
        values.append(job_id)
        with self._lock, get_connection() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", tuple(values))
            conn.commit()

    def add_event(
        self,
        job_id: str,
        event_type: str,
        stage: str | None,
        payload: dict[str, Any],
        created_at: float | None = None,
    ) -> None:
        created = created_at or time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_events (job_id, event_type, stage, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, event_type, stage, json.dumps(payload), created),
            )
            conn.commit()

    def list_events(self, job_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        with self._lock, get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_events
                WHERE job_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def add_log(
        self,
        job_id: str,
        level: str,
        source: str,
        message: str,
        meta: dict[str, Any] | None = None,
        created_at: float | None = None,
    ) -> None:
        created = created_at or time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_logs (job_id, level, source, message, meta_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, level, source, message, json.dumps(meta or {}), created),
            )
            conn.commit()

    def list_logs(self, job_id: str, limit: int = 2000) -> list[dict[str, Any]]:
        with self._lock, get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_logs
                WHERE job_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def add_artifact(
        self,
        job_id: str,
        artifact_type: str,
        content_text: str,
        artifact_key: str | None = None,
        created_at: float | None = None,
    ) -> None:
        created = created_at or time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_artifacts (job_id, artifact_type, artifact_key, content_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, artifact_type, artifact_key, content_text, created),
            )
            conn.commit()

    def list_artifacts(self, job_id: str, limit: int = 500) -> list[dict[str, Any]]:
        with self._lock, get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_artifacts
                WHERE job_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def create_decision(
        self,
        job_id: str,
        stage: str,
        decision_type: str,
        required: bool,
        prompt: dict[str, Any],
        status: str = "pending",
    ) -> None:
        now = time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_decisions
                (job_id, stage, decision_type, required, status, prompt_json, response_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, stage, decision_type, int(required), status, json.dumps(prompt), "{}", now),
            )
            conn.commit()

    def resolve_decision(self, job_id: str, stage: str, response: dict[str, Any], status: str = "approved") -> None:
        now = time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                UPDATE job_decisions
                SET status = ?, response_json = ?, resolved_at = ?
                WHERE job_id = ? AND stage = ? AND status = 'pending'
                """,
                (status, json.dumps(response), now, job_id, stage),
            )
            conn.commit()

    def list_decisions(self, job_id: str, limit: int = 500) -> list[dict[str, Any]]:
        with self._lock, get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_decisions
                WHERE job_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def create_agent_message(
        self,
        job_id: str,
        from_agent: str,
        to_agent: str,
        message_type: str,
        topic: str,
        content: dict[str, Any] | None = None,
        *,
        status: str = "pending",
        blocking: bool = False,
        created_at: float | None = None,
    ) -> dict[str, Any] | None:
        created = created_at or time.time()
        with self._lock, get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agent_messages (
                    job_id, from_agent, to_agent, message_type, topic, content_json,
                    status, blocking, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    from_agent,
                    to_agent,
                    message_type,
                    topic,
                    json.dumps(content or {}),
                    status,
                    int(blocking),
                    created,
                ),
            )
            message_id = cursor.lastrowid
            conn.commit()
        if message_id is None:
            return None
        return self.get_agent_message(int(message_id))

    def get_agent_message(self, message_id: int) -> dict[str, Any] | None:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_messages WHERE id = ?", (message_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def list_agent_messages(self, job_id: str, *, status: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        with self._lock, get_connection() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM agent_messages
                    WHERE job_id = ? AND status = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (job_id, status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM agent_messages
                    WHERE job_id = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (job_id, limit),
                ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def resolve_agent_message(
        self,
        job_id: str,
        message_id: int,
        decision: dict[str, Any],
        *,
        status: str = "resolved",
        resolved_at: float | None = None,
    ) -> dict[str, Any] | None:
        now = resolved_at or time.time()
        current = self.get_agent_message(message_id)
        if not current or current.get("job_id") != job_id:
            return None

        content = current.get("content_json") or {}
        if not isinstance(content, dict):
            content = {}
        updated_content = {**content, "decision": decision}

        with self._lock, get_connection() as conn:
            conn.execute(
                """
                UPDATE agent_messages
                SET status = ?, resolved_at = ?, content_json = ?
                WHERE id = ? AND job_id = ?
                """,
                (status, now, json.dumps(updated_content), message_id, job_id),
            )
            conn.commit()
        return self.get_agent_message(message_id)

    def escalate_agent_message(
        self,
        job_id: str,
        message_id: int,
        reason: str,
        *,
        escalated_by: str = "agent_coordinator",
        escalated_at: float | None = None,
    ) -> dict[str, Any] | None:
        """Mark an agent message as escalated with escalation metadata."""
        return self.resolve_agent_message(
            job_id=job_id,
            message_id=message_id,
            decision={
                "status": "escalated",
                "rationale": reason,
                "metadata": {"escalated_by": escalated_by},
            },
            status="escalated",
            resolved_at=escalated_at,
        )

    def get_app_setting(self, key: str) -> dict[str, Any] | None:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM app_settings WHERE key = ?", (key,)).fetchone()
        return _row_to_dict(row) if row else None

    def upsert_app_setting(self, key: str, value: dict[str, Any], updated_at: float | None = None) -> None:
        now = updated_at or time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(value), now),
            )
            conn.commit()

    def get_job_context_settings(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM job_context_settings WHERE job_id = ?", (job_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def get_job_reasoning_settings(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM job_reasoning_settings WHERE job_id = ?", (job_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def upsert_job_reasoning_settings(
        self,
        job_id: str,
        *,
        use_global_defaults: bool,
        override: dict[str, Any] | None,
        launch_override: dict[str, Any] | None,
        updated_at: float | None = None,
    ) -> None:
        now = updated_at or time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_reasoning_settings (
                    job_id, use_global_defaults, override_json, launch_override_json, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    use_global_defaults = excluded.use_global_defaults,
                    override_json = excluded.override_json,
                    launch_override_json = excluded.launch_override_json,
                    updated_at = excluded.updated_at
                """,
                (
                    job_id,
                    int(use_global_defaults),
                    json.dumps(override or {}),
                    json.dumps(launch_override or {}),
                    now,
                ),
            )
            conn.commit()

    def upsert_job_context_settings(
        self,
        job_id: str,
        *,
        use_global_defaults: bool,
        override: dict[str, Any] | None,
        updated_at: float | None = None,
    ) -> None:
        now = updated_at or time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_context_settings (job_id, use_global_defaults, override_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    use_global_defaults = excluded.use_global_defaults,
                    override_json = excluded.override_json,
                    updated_at = excluded.updated_at
                """,
                (job_id, int(use_global_defaults), json.dumps(override or {}), now),
            )
            conn.commit()

    def get_job_context_state(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, get_connection() as conn:
            row = conn.execute("SELECT * FROM job_context_state WHERE job_id = ?", (job_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def upsert_job_context_state(
        self,
        job_id: str,
        *,
        estimated_tokens: int,
        limit_tokens: int,
        fill_percent: float,
        last_compacted_at: float | None = None,
        compaction_count: int | None = None,
        last_summary_text: str | None = None,
        last_compaction_before_percent: float | None = None,
        last_compaction_after_percent: float | None = None,
        updated_at: float | None = None,
    ) -> None:
        now = updated_at or time.time()
        existing = self.get_job_context_state(job_id)
        effective_count = int(compaction_count if compaction_count is not None else (existing or {}).get("compaction_count", 0))
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_context_state (
                    job_id, estimated_tokens, limit_tokens, fill_percent, last_compacted_at,
                    compaction_count, last_summary_text, last_compaction_before_percent,
                    last_compaction_after_percent, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    estimated_tokens = excluded.estimated_tokens,
                    limit_tokens = excluded.limit_tokens,
                    fill_percent = excluded.fill_percent,
                    last_compacted_at = COALESCE(excluded.last_compacted_at, job_context_state.last_compacted_at),
                    compaction_count = excluded.compaction_count,
                    last_summary_text = COALESCE(excluded.last_summary_text, job_context_state.last_summary_text),
                    last_compaction_before_percent = COALESCE(excluded.last_compaction_before_percent, job_context_state.last_compaction_before_percent),
                    last_compaction_after_percent = COALESCE(excluded.last_compaction_after_percent, job_context_state.last_compaction_after_percent),
                    updated_at = excluded.updated_at
                """,
                (
                    job_id,
                    int(estimated_tokens),
                    int(limit_tokens),
                    float(fill_percent),
                    last_compacted_at,
                    effective_count,
                    last_summary_text,
                    last_compaction_before_percent,
                    last_compaction_after_percent,
                    now,
                ),
            )
            conn.commit()

    def add_job_context_compaction(
        self,
        job_id: str,
        *,
        before_tokens: int,
        after_tokens: int,
        before_fill_percent: float,
        after_fill_percent: float,
        summary_text: str,
        metadata: dict[str, Any] | None = None,
        created_at: float | None = None,
    ) -> None:
        created = created_at or time.time()
        with self._lock, get_connection() as conn:
            conn.execute(
                """
                INSERT INTO job_context_compactions (
                    job_id, before_tokens, after_tokens, before_fill_percent,
                    after_fill_percent, summary_text, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    int(before_tokens),
                    int(after_tokens),
                    float(before_fill_percent),
                    float(after_fill_percent),
                    summary_text,
                    json.dumps(metadata or {}),
                    created,
                ),
            )
            conn.commit()

    def list_job_context_compactions(self, job_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock, get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_context_compactions
                WHERE job_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


_repository: CommandCenterRepository | None = None


def get_repository() -> CommandCenterRepository:
    """Get singleton repository."""
    global _repository
    if _repository is None:
        _repository = CommandCenterRepository()
    return _repository
