"""SQLite setup and connection helpers for Command Center."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "karkhana.db"


def get_connection() -> sqlite3.Connection:
    """Create a sqlite connection with Row mapping."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize schema and indexes if they do not exist."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                idea TEXT NOT NULL,
                status TEXT NOT NULL,
                approval_required INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                started_at REAL,
                finished_at REAL,
                stopped_at REAL,
                error_message TEXT,
                progress_percent REAL NOT NULL DEFAULT 0,
                current_stage TEXT,
                label TEXT
            );

            CREATE TABLE IF NOT EXISTS job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                stage TEXT,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                message TEXT NOT NULL,
                meta_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                artifact_key TEXT,
                content_text TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                required INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL,
                prompt_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                resolved_at REAL
            );

            CREATE TABLE IF NOT EXISTS agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                message_type TEXT NOT NULL,
                topic TEXT NOT NULL,
                content_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                blocking INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                resolved_at REAL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_context_settings (
                job_id TEXT PRIMARY KEY,
                use_global_defaults INTEGER NOT NULL DEFAULT 1,
                override_json TEXT NOT NULL DEFAULT '{}',
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_context_state (
                job_id TEXT PRIMARY KEY,
                estimated_tokens INTEGER NOT NULL DEFAULT 0,
                limit_tokens INTEGER NOT NULL DEFAULT 128000,
                fill_percent REAL NOT NULL DEFAULT 0,
                last_compacted_at REAL,
                compaction_count INTEGER NOT NULL DEFAULT 0,
                last_summary_text TEXT,
                last_compaction_before_percent REAL,
                last_compaction_after_percent REAL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_context_compactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                before_tokens INTEGER NOT NULL,
                after_tokens INTEGER NOT NULL,
                before_fill_percent REAL NOT NULL,
                after_fill_percent REAL NOT NULL,
                summary_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_reasoning_settings (
                job_id TEXT PRIMARY KEY,
                use_global_defaults INTEGER NOT NULL DEFAULT 1,
                override_json TEXT NOT NULL DEFAULT '{}',
                launch_override_json TEXT NOT NULL DEFAULT '{}',
                updated_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_status_created
                ON jobs(status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_job_events_job_created
                ON job_events(job_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_job_logs_job_created
                ON job_logs(job_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_job_decisions_job_status
                ON job_decisions(job_id, status);
            CREATE INDEX IF NOT EXISTS idx_agent_messages_job_created
                ON agent_messages(job_id, created_at ASC);
            CREATE INDEX IF NOT EXISTS idx_agent_messages_job_status
                ON agent_messages(job_id, status);
            CREATE INDEX IF NOT EXISTS idx_job_context_compactions_job_created
                ON job_context_compactions(job_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_job_reasoning_settings_updated
                ON job_reasoning_settings(updated_at DESC);
            """
        )
        conn.commit()
