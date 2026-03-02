"""Job-scoped context tracking with threshold-triggered compaction."""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from typing import Any

import tiktoken

from src.command_center.models import (
    CompactionPriorityWeights,
    ContextCompactionConfig,
    ContextUsageSnapshot,
    JobContextConfig,
)
from src.command_center.repository import get_repository
from src.llm.context_units import tk_to_tokens


GLOBAL_SETTINGS_KEY = "context_compaction_defaults"
_TIMELINE_STAGES = [
    "pm_agent",
    "pm_consensus",
    "architect_agent",
    "taskmaster",
    "coder_agent",
    "reviewer_agent",
    "sandbox_executor",
]


class ContextManager:
    """Tracks prompt memory and compacts it when configured thresholds are reached."""

    _instance: "ContextManager | None" = None

    def __init__(self) -> None:
        self.repo = get_repository()
        self._job_blocks: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._calls_since_compaction: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    @classmethod
    def get(cls) -> "ContextManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def get_global_defaults(self) -> ContextCompactionConfig:
        row = self.repo.get_app_setting(GLOBAL_SETTINGS_KEY)
        if not row:
            return ContextCompactionConfig()
        value = row.get("value_json") or {}
        if not isinstance(value, dict):
            return ContextCompactionConfig()
        return ContextCompactionConfig.model_validate(value)

    def set_global_defaults(self, cfg: ContextCompactionConfig) -> ContextCompactionConfig:
        self.repo.upsert_app_setting(GLOBAL_SETTINGS_KEY, cfg.model_dump())
        return cfg

    def get_job_config(self, job_id: str) -> JobContextConfig:
        row = self.repo.get_job_context_settings(job_id)
        if not row:
            return JobContextConfig(job_id=job_id, use_global_defaults=True, override=None)

        raw_override = row.get("override_json") or {}
        override = None
        if isinstance(raw_override, dict) and raw_override:
            override = ContextCompactionConfig.model_validate(raw_override)
        return JobContextConfig(
            job_id=job_id,
            use_global_defaults=bool(row.get("use_global_defaults", True)),
            override=override,
        )

    def set_job_config(
        self,
        job_id: str,
        *,
        use_global_defaults: bool,
        override: ContextCompactionConfig | None,
    ) -> JobContextConfig:
        self.repo.upsert_job_context_settings(
            job_id,
            use_global_defaults=use_global_defaults,
            override=override.model_dump() if override else {},
        )
        return JobContextConfig(job_id=job_id, use_global_defaults=use_global_defaults, override=override)

    def get_effective_config(self, job_id: str) -> ContextCompactionConfig:
        job_cfg = self.get_job_config(job_id)
        if not job_cfg.use_global_defaults and job_cfg.override is not None:
            return job_cfg.override
        return self.get_global_defaults()

    async def initialize_job(self, job_id: str, raw_idea: str) -> None:
        if not job_id:
            return
        cfg = self.get_effective_config(job_id)
        async with self._lock:
            if not self._job_blocks[job_id]:
                self._job_blocks[job_id].append(
                    {
                        "type": "user_intent",
                        "content": raw_idea,
                        "stage": "start",
                        "created_at": time.time(),
                        "metadata": {"source": "job_init"},
                    }
                )
            self._calls_since_compaction[job_id] = 0
            await self._persist_usage_locked(job_id, cfg)

    async def prepare_messages(
        self,
        job_id: str | None,
        messages: list[dict[str, Any]],
        *,
        stage: str | None = None,
        context_type: str = "agent_call",
    ) -> list[dict[str, Any]]:
        if not job_id:
            return messages

        async with self._lock:
            cfg = self.get_effective_config(job_id)
            text = self._serialize_messages(messages)
            self._job_blocks[job_id].append(
                {
                    "type": context_type,
                    "content": text,
                    "stage": stage,
                    "created_at": time.time(),
                    "metadata": {"source": "prompt"},
                }
            )
            self._calls_since_compaction[job_id] += 1
            await self._persist_usage_locked(job_id, cfg)
            await self._maybe_compact_locked(job_id, cfg)
            memory_text = self._render_working_memory(job_id)

        if not memory_text:
            return messages

        memory_message = {
            "role": "system",
            "content": (
                "Working memory context (auto-compacted when needed). "
                "Preserve user intent, coding progress, timeline decisions, and unresolved risks.\n\n"
                f"{memory_text}"
            ),
        }
        return [memory_message, *messages]

    async def observe_event(self, job_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        if not job_id:
            return
        if event_type.startswith("context_"):
            return

        async with self._lock:
            cfg = self.get_effective_config(job_id)
            block_type = self._event_type_to_block_type(event_type)
            content = self._event_to_content(event_type, payload)
            if not content:
                return
            self._job_blocks[job_id].append(
                {
                    "type": block_type,
                    "content": content,
                    "stage": payload.get("stage"),
                    "created_at": time.time(),
                    "metadata": {"event_type": event_type, **(payload or {})},
                }
            )
            await self._persist_usage_locked(job_id, cfg)
            await self._maybe_compact_locked(job_id, cfg)

    def get_usage_snapshot(self, job_id: str) -> ContextUsageSnapshot:
        row = self.repo.get_job_context_state(job_id)
        cfg = self.get_effective_config(job_id)
        limit_tokens = tk_to_tokens(cfg.context_limit_tk)
        if not row:
            return ContextUsageSnapshot(
                job_id=job_id,
                estimated_tokens=0,
                limit_tokens=limit_tokens,
                fill_percent=0.0,
                last_compacted_at=None,
                compaction_count=0,
                last_summary_text=None,
                last_compaction_before_percent=None,
                last_compaction_after_percent=None,
            )

        return ContextUsageSnapshot(
            job_id=job_id,
            estimated_tokens=int(row.get("estimated_tokens", 0)),
            limit_tokens=int(row.get("limit_tokens", limit_tokens)),
            fill_percent=float(row.get("fill_percent", 0.0)),
            last_compacted_at=row.get("last_compacted_at"),
            compaction_count=int(row.get("compaction_count", 0)),
            last_summary_text=row.get("last_summary_text"),
            last_compaction_before_percent=row.get("last_compaction_before_percent"),
            last_compaction_after_percent=row.get("last_compaction_after_percent"),
        )

    def list_compactions(self, job_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.repo.list_job_context_compactions(job_id, limit=limit)

    async def _persist_usage_locked(self, job_id: str, cfg: ContextCompactionConfig) -> None:
        usage = self._usage_for_job(job_id, cfg)
        self.repo.upsert_job_context_state(
            job_id,
            estimated_tokens=usage["estimated_tokens"],
            limit_tokens=usage["limit_tokens"],
            fill_percent=usage["fill_percent"],
        )
        await self._emit(
            "context_usage_updated",
            {
                "job_id": job_id,
                "estimated_tokens": usage["estimated_tokens"],
                "limit_tokens": usage["limit_tokens"],
                "fill_percent": usage["fill_percent"],
            },
        )

    async def _maybe_compact_locked(self, job_id: str, cfg: ContextCompactionConfig) -> None:
        blocks = self._job_blocks[job_id]
        if len(blocks) < cfg.min_messages_to_compact:
            return

        usage = self._usage_for_job(job_id, cfg)
        fill = usage["fill_percent"]
        if fill < cfg.trigger_fill_percent:
            return

        if self._calls_since_compaction[job_id] < cfg.cooldown_calls:
            return

        await self._compact_locked(job_id, cfg, usage)

    async def _compact_locked(self, job_id: str, cfg: ContextCompactionConfig, before_usage: dict[str, Any]) -> None:
        before_tokens = int(before_usage["estimated_tokens"])
        before_fill = float(before_usage["fill_percent"])

        await self._emit(
            "context_compaction_started",
            {
                "job_id": job_id,
                "before_tokens": before_tokens,
                "before_fill_percent": before_fill,
                "target_fill_percent": cfg.target_fill_percent,
            },
        )

        try:
            limit_tokens = tk_to_tokens(cfg.context_limit_tk)
            target_tokens = int(limit_tokens * (cfg.target_fill_percent / 100.0))
            blocks = list(self._job_blocks[job_id])
            anchors = self._anchor_indices(blocks)

            retained = [block for idx, block in enumerate(blocks) if idx in anchors]
            non_anchor = [(idx, block) for idx, block in enumerate(blocks) if idx not in anchors]
            scored = sorted(
                non_anchor,
                key=lambda pair: self._priority_score(pair[1], cfg.priority_weights),
                reverse=True,
            )

            dropped: list[dict[str, Any]] = []
            for _, block in scored:
                candidate = [*retained, block]
                if self._estimate_blocks_tokens(candidate) <= int(target_tokens * 0.68):
                    retained.append(block)
                else:
                    dropped.append(block)

            summary_text = self._summarize_blocks(dropped, tight=False)
            summary_block = {
                "type": "summary",
                "content": summary_text,
                "stage": "context_compaction",
                "created_at": time.time(),
                "metadata": {"source": "compaction"},
            }
            compacted = sorted([*retained, summary_block], key=lambda b: float(b.get("created_at", 0.0)))

            if self._estimate_blocks_tokens(compacted) > target_tokens:
                summary_block["content"] = self._summarize_blocks(dropped, tight=True)

            if self._estimate_blocks_tokens(compacted) > target_tokens:
                compacted = self._trim_to_target(compacted, target_tokens)

            after_tokens = self._estimate_blocks_tokens(compacted)
            after_fill = self._fill_percent(after_tokens, limit_tokens)

            self._job_blocks[job_id] = compacted
            self._calls_since_compaction[job_id] = 0
            state = self.repo.get_job_context_state(job_id) or {}
            new_count = int(state.get("compaction_count", 0)) + 1

            self.repo.upsert_job_context_state(
                job_id,
                estimated_tokens=after_tokens,
                limit_tokens=limit_tokens,
                fill_percent=after_fill,
                last_compacted_at=time.time(),
                compaction_count=new_count,
                last_summary_text=summary_block["content"],
                last_compaction_before_percent=before_fill,
                last_compaction_after_percent=after_fill,
            )
            self.repo.add_job_context_compaction(
                job_id,
                before_tokens=before_tokens,
                after_tokens=after_tokens,
                before_fill_percent=before_fill,
                after_fill_percent=after_fill,
                summary_text=summary_block["content"],
                metadata={"target_fill_percent": cfg.target_fill_percent},
            )

            await self._emit(
                "context_compaction_completed",
                {
                    "job_id": job_id,
                    "before_tokens": before_tokens,
                    "after_tokens": after_tokens,
                    "before_fill_percent": before_fill,
                    "after_fill_percent": after_fill,
                    "summary_text": summary_block["content"],
                    "summary_size_chars": len(summary_block["content"]),
                },
            )
        except Exception as exc:
            await self._emit(
                "context_compaction_failed",
                {
                    "job_id": job_id,
                    "before_tokens": before_tokens,
                    "before_fill_percent": before_fill,
                    "message": str(exc),
                },
            )

    def _render_working_memory(self, job_id: str, max_blocks: int = 14) -> str:
        blocks = self._job_blocks[job_id][-max_blocks:]
        rendered: list[str] = []
        for block in blocks:
            block_type = str(block.get("type") or "context")
            stage = str(block.get("stage") or "-")
            content = str(block.get("content") or "").strip()
            if not content:
                continue
            rendered.append(f"[{block_type} | {stage}] {content[:700]}")
        return "\n".join(rendered)

    def _usage_for_job(self, job_id: str, cfg: ContextCompactionConfig) -> dict[str, Any]:
        estimated_tokens = self._estimate_blocks_tokens(self._job_blocks[job_id])
        limit_tokens = tk_to_tokens(cfg.context_limit_tk)
        fill = self._fill_percent(estimated_tokens, limit_tokens)
        return {
            "estimated_tokens": estimated_tokens,
            "limit_tokens": limit_tokens,
            "fill_percent": fill,
        }

    def _estimate_blocks_tokens(self, blocks: list[dict[str, Any]]) -> int:
        combined = "\n".join(self._serialize_block(b) for b in blocks)
        return self._estimate_tokens(combined)

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                encoding = tiktoken.encoding_for_model("gpt-4o-mini")
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _serialize_messages(self, messages: list[dict[str, Any]]) -> str:
        rendered: list[str] = []
        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            if not isinstance(content, str):
                try:
                    content = json.dumps(content, ensure_ascii=False)
                except Exception:
                    content = str(content)
            rendered.append(f"{role}: {content}")
        return "\n".join(rendered)

    def _serialize_block(self, block: dict[str, Any]) -> str:
        return f"[{block.get('type')}|{block.get('stage')}] {block.get('content', '')}"

    def _event_type_to_block_type(self, event_type: str) -> str:
        mapping = {
            "build_started": "timeline_event",
            "stage_start": "timeline_event",
            "stage_complete": "timeline_event",
            "stage_output": "timeline_event",
            "code_generated": "coding_artifact",
            "review_result": "review",
            "waiting_for_approval": "risk",
            "stage_approved": "timeline_event",
            "error": "risk",
            "agent_message_created": "agent_message",
            "agent_message_escalated": "risk",
            "tool_call": "agent_call",
            "tool_result": "agent_call",
        }
        return mapping.get(event_type, "timeline_event")

    def _event_to_content(self, event_type: str, payload: dict[str, Any]) -> str:
        stage = payload.get("stage")
        if event_type == "build_started":
            return f"Build started for idea: {payload.get('idea', '')}"
        if event_type == "stage_start":
            return f"Stage started: {stage}"
        if event_type == "stage_complete":
            return f"Stage completed: {stage}"
        if event_type == "stage_output":
            output = payload.get("output")
            text = str(output)
            return f"Stage output ({stage}): {text[:1000]}"
        if event_type == "code_generated":
            path = payload.get("file_path") or payload.get("file")
            code = str(payload.get("code", ""))
            return f"Generated code for {path}: {code[:1200]}"
        if event_type == "review_result":
            return f"Review for {payload.get('file')}: passed={payload.get('passed')} issues={payload.get('issues')}"
        if event_type == "waiting_for_approval":
            return f"Waiting approval at {stage}: {payload.get('data')}"
        if event_type == "stage_approved":
            return f"Approval resolved for {stage}."
        if event_type == "error":
            return f"Error at {stage}: {payload.get('message', payload.get('error', 'unknown'))}"
        if event_type == "agent_message_created":
            return f"Agent message: {payload.get('message_type')} topic={payload.get('topic')}"
        if event_type == "agent_message_escalated":
            return f"Agent message escalated: id={payload.get('message_id')} reason={payload.get('escalation_reason')}"
        if event_type == "tool_call":
            return f"Tool call: {payload.get('tool_name')} args={payload.get('arguments')}"
        if event_type == "tool_result":
            return f"Tool result: {payload.get('tool_name')} result={payload.get('result')}"
        return ""

    def _anchor_indices(self, blocks: list[dict[str, Any]]) -> set[int]:
        anchors: set[int] = set()
        latest_user_intent = None
        latest_coding = None

        for idx, block in enumerate(blocks):
            block_type = str(block.get("type") or "")
            if block_type == "user_intent":
                latest_user_intent = idx
            if block_type == "coding_artifact":
                latest_coding = idx
            if block_type == "risk":
                metadata = block.get("metadata") or {}
                if isinstance(metadata, dict) and metadata.get("blocking"):
                    anchors.add(idx)

        if latest_user_intent is not None:
            anchors.add(latest_user_intent)
        if latest_coding is not None:
            anchors.add(latest_coding)

        # Keep one timeline milestone per stage where available.
        stage_seen: set[str] = set()
        for idx in range(len(blocks) - 1, -1, -1):
            stage = str(blocks[idx].get("stage") or "")
            block_type = str(blocks[idx].get("type") or "")
            if block_type != "timeline_event":
                continue
            if stage in _TIMELINE_STAGES and stage not in stage_seen:
                anchors.add(idx)
                stage_seen.add(stage)

        return anchors

    def _priority_score(self, block: dict[str, Any], weights: CompactionPriorityWeights) -> float:
        block_type = str(block.get("type") or "")
        mapping = {
            "coding_artifact": float(weights.coding_context),
            "agent_call": float(weights.coding_context),
            "review": float(weights.coding_context),
            "user_intent": float(weights.user_intent),
            "timeline_event": float(weights.timeline_continuity),
            "risk": float(weights.open_risks),
            "agent_message": float(weights.open_risks),
            "summary": 100.0,
        }
        base = mapping.get(block_type, 5.0)
        created = float(block.get("created_at") or time.time())
        age_seconds = max(0.0, time.time() - created)
        recency_bonus = max(0.0, 15.0 - (age_seconds / 30.0))
        return base + recency_bonus

    def _summarize_blocks(self, blocks: list[dict[str, Any]], *, tight: bool) -> str:
        if not blocks:
            return "No lower-priority context was compacted in this pass."

        max_item_len = 100 if tight else 220
        grouped: dict[str, list[str]] = defaultdict(list)
        for block in blocks:
            key = str(block.get("type") or "context")
            text = str(block.get("content") or "").replace("\n", " ").strip()
            if text:
                grouped[key].append(text[:max_item_len])

        parts: list[str] = ["Compacted context summary:"]
        for key in sorted(grouped.keys()):
            values = grouped[key][: (2 if tight else 4)]
            joined = " | ".join(values)
            parts.append(f"- {key}: {joined}")

        parts.append(
            "- timeline: PM -> Architect -> Taskmaster -> Coder -> Reviewer -> Sandbox progression retained with major decisions and next action context."
        )
        return "\n".join(parts)

    def _trim_to_target(self, blocks: list[dict[str, Any]], target_tokens: int) -> list[dict[str, Any]]:
        out = list(blocks)
        while len(out) > 2 and self._estimate_blocks_tokens(out) > target_tokens:
            removable_idx = None
            removable_score = float("inf")
            for idx, block in enumerate(out):
                block_type = str(block.get("type") or "")
                if block_type in {"user_intent", "summary"}:
                    continue
                score = self._priority_score(block, CompactionPriorityWeights())
                if score < removable_score:
                    removable_score = score
                    removable_idx = idx
            if removable_idx is None:
                break
            out.pop(removable_idx)

        if self._estimate_blocks_tokens(out) > target_tokens:
            for block in out:
                if str(block.get("type")) == "summary":
                    content = str(block.get("content") or "")
                    while len(content) > 120 and self._estimate_blocks_tokens(out) > target_tokens:
                        content = content[: int(len(content) * 0.8)]
                        block["content"] = content
        return out

    def _fill_percent(self, estimated_tokens: int, limit_tokens: int) -> float:
        if limit_tokens <= 0:
            return 0.0
        return round((estimated_tokens / limit_tokens) * 100.0, 2)

    async def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from src.dashboard.event_bus import EventBus

            await EventBus.get().emit(event_type, payload)
        except Exception:
            pass
