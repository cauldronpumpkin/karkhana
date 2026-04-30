from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.app.repository import (
    AUTONOMY_AUTONOMOUS_DEVELOPMENT,
    ArtifactMetadata,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    Intent,
    ProjectTwin,
    ResearchArtifact,
    TemplateArtifact,
    TemplatePack,
    WorkItem,
    WorkerEvent,
    get_repository,
    utcnow,
)
from backend.app.services.agents_md_artifact import AgentsMdArtifactService
from backend.app.services.ai_roles import FactoryRole, RolePromptBuilder
from backend.app.services.autonomy import (
    HIGH_AUTONOMY_LEVELS,
    can_enqueue_work,
    validate_engine_for_autonomy_level,
)
from backend.app.services.factory_tracking import (
    FACTORY_WORKER_JOB_TYPE,
    collect_factory_run_bundle,
    refresh_factory_run_tracking_manifest,
)
from backend.app.services.factory_run_ledger import extract_compact_ledger_context, validate_ledger_metadata
from backend.app.services.template_pack import TemplatePackService
from backend.app.services.policy_engine import (
    KNOWN_WORKER_CAPABILITIES,
    PolicyBlockedError,
    ProjectBlueprint,
    PythonPolicyEngine,
    RING_0_READONLY,
    RING_1_SCOPED_EXECUTION,
    RING_2_TOOL_INTEGRATION,
    RING_3_HIGH_RISK_APPROVAL,
    WorkerPermissionProfile,
)
from backend.app.services.project_twin import ProjectTwinService, to_jsonable


class FactoryRunService:
    def __init__(self) -> None:
        self._project_service = ProjectTwinService()
        self._policy_engine = PythonPolicyEngine()
        self._template_service = TemplatePackService()

    async def _build_template_context(self, template: TemplatePack, *, target_path: str = ".") -> dict[str, Any]:
        repo = get_repository()
        template_docs = await self._collect_template_docs(repo, template.template_id)
        template_manifest_record = await repo.get_template_manifest(template.template_id, template.version)
        template_manifest = dict(template_manifest_record.metadata_ or {}) if template_manifest_record and template_manifest_record.metadata_ else {}
        if not template_manifest.get("id"):
            template_manifest = {
                "id": template.template_id,
                "template_id": template.template_id,
                "version": template.version,
                "display_name": template.display_name,
                "verification_commands": list((template.opencode_worker or {}).get("verification_commands") or []),
                "graphify_expectations": {
                    "read_before_task": [
                        "graphify-out/GRAPH_REPORT.md",
                        "graphify-out/wiki/index.md",
                    ],
                    "refresh_after_task": ["graphify update ."],
                },
                "allowed_paths": ["backend/**", "frontend/**", "docs/**", "scripts/**", "tests/**"],
                "forbidden_paths": [".karkhana/**"],
                "review_metadata": {"template_id": template.template_id, "template_version": template.version},
            }
        verification_commands = list(template_manifest.get("verification_commands") or template.opencode_worker.get("verification_commands") or [])
        if "graphify update ." not in verification_commands:
            verification_commands.append("graphify update .")
        graphify_expectations = dict(template_manifest.get("graphify_expectations") or {
            "read_before_task": [
                "graphify-out/GRAPH_REPORT.md",
                "graphify-out/wiki/index.md",
            ],
            "refresh_after_task": ["graphify update ."],
        })
        path_guardrails = self._normalize_path_guardrails(
            {
                "allowed_paths": template_manifest.get("allowed_paths") or [],
                "forbidden_paths": template_manifest.get("forbidden_paths") or [],
            },
            template_manifest,
        )
        resolved_agents = [
            doc
            for doc in template_docs
            if str(doc.get("key") or "").strip() in {"AGENTS.md", "AGENTS.override.md"}
        ]
        return {
            "template_manifest": template_manifest,
            "verification_commands": verification_commands,
            "graphify_expectations": graphify_expectations,
            "path_guardrails": path_guardrails,
            "resolved_agents": resolved_agents,
            "review_metadata": dict(template_manifest.get("review_metadata") or {}),
        }

    async def create_factory_run(
        self,
        project_id: str,
        template_id: str,
        autonomy_level: str = AUTONOMY_AUTONOMOUS_DEVELOPMENT,
        config: dict[str, Any] | None = None,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repo = get_repository()
        project = await repo.get_project_twin_by_id(project_id)
        if not project:
            raise ValueError("Project twin not found")

        template = await repo.get_template_pack(template_id)
        if not template:
            raise ValueError("Template pack not found")
        template_context = await self._build_template_context(template, target_path=".")
        code_index = await repo.get_latest_code_index(project.idea_id)

        config = dict(config or {})
        intent_record: Intent | None = None
        intent_payload = dict(intent or {})
        if intent_payload:
            intent_summary = str(
                intent_payload.get("summary")
                or intent_payload.get("goal")
                or intent_payload.get("description")
                or config.get("goal")
                or (template.opencode_worker or {}).get("goal")
                or ""
            ).strip()
            if not intent_summary:
                raise ValueError("Intent summary is required")
            intent_budget = dict(intent_payload.get("budget") or config.get("budget") or {})
            intent_stop_conditions = list(intent_payload.get("stop_conditions") or config.get("stop_conditions") or [])
            intent_record = Intent(
                idea_id=project.idea_id,
                project_id=project_id,
                summary=intent_summary,
                details=dict(intent_payload.get("details") or {}),
                correlation_id=str(intent_payload.get("correlation_id") or config.get("correlation_id") or ""),
                dedupe_hash=self._stable_hash({
                    "idea_id": project.idea_id,
                    "project_id": project_id,
                    "template_id": template.template_id,
                    "template_version": template.version,
                    "summary": intent_summary,
                    "budget": intent_budget,
                    "stop_conditions": intent_stop_conditions,
                }),
                budget=intent_budget,
                stop_conditions=intent_stop_conditions,
                source=str(intent_payload.get("source") or "manual"),
            )
            await repo.save_intent(intent_record)
            config.setdefault("goal", intent_summary)
            config["intent"] = {
                "id": intent_record.id,
                "summary": intent_record.summary,
                "details": intent_record.details,
                "correlation_id": intent_record.correlation_id,
                "dedupe_hash": intent_record.dedupe_hash,
            }

        engine = config.get("engine", "opencode-server")
        if autonomy_level in HIGH_AUTONOMY_LEVELS:
            try:
                validate_engine_for_autonomy_level(engine, autonomy_level)
            except ValueError:
                validate_engine_for_autonomy_level("opencode-server", autonomy_level)
        blueprint = await self._build_project_blueprint(
            project=project,
            template=template,
            config=config,
            template_context=template_context,
        )
        policy_result = self._policy_engine.validate_blueprint(
            blueprint,
            project=project,
            template=template,
        )
        if policy_result.status == "block":
            raise PolicyBlockedError(policy_result)

        template_manifest = dict((template_context or {}).get("template_manifest") or {})
        if not template_manifest.get("id"):
            template_manifest = {
                "id": template.template_id,
                "template_id": template.template_id,
                "version": template.version,
                "display_name": template.display_name,
                "verification_commands": list((template.opencode_worker or {}).get("verification_commands") or []),
                "graphify_expectations": dict((template_context or {}).get("graphify_expectations") or {}),
                "allowed_paths": list((template_context or {}).get("path_guardrails", {}).get("allowed_paths") or []),
                "forbidden_paths": list((template_context or {}).get("path_guardrails", {}).get("forbidden_paths") or []),
                "review_metadata": dict((template_context or {}).get("review_metadata") or {}),
            }
        path_guardrails = self._normalize_path_guardrails((template_context or {}).get("path_guardrails"), template_manifest)
        initial_phase_key = self._initial_phase_key(template)
        scaffold_manifest = self._build_scaffold_manifest(
            factory_run_id="<pending>",
            template=template,
            project_blueprint=to_jsonable(blueprint),
            template_context=template_context,
            code_index=code_index,
            phase_key=initial_phase_key,
            batch_key=f"{initial_phase_key}-batch-1",
        )

        ledger_metadata = validate_ledger_metadata(config)

        run_config = {
            **config,
            "autonomy_level": autonomy_level,
            "template_version": template.version,
            "template_id": template.template_id,
            "ledger_policy": ledger_metadata["ledger_policy"],
            "ledger_path": ledger_metadata["ledger_path"],
            "template_manifest": template_manifest,
            "verification_commands": template_context.get("verification_commands") if template_context else [],
            "graphify_expectations": template_context.get("graphify_expectations") if template_context else {},
            "path_guardrails": path_guardrails,
            "resolved_agents_hierarchy": template_context.get("resolved_agents") if template_context else [],
            "review_metadata": template_context.get("review_metadata") if template_context else {},
            "project_blueprint": to_jsonable(blueprint),
            "policy_result": policy_result.to_dict(),
            "scaffold_manifest": scaffold_manifest,
        }
        if intent_record:
            run_config["intent_id"] = intent_record.id
            run_config["intent_summary"] = intent_record.summary
            run_config["intent_details"] = intent_record.details
            run_config["budget"] = intent_record.budget
            run_config["stop_conditions"] = intent_record.stop_conditions
        run_config.setdefault("goal", config.get("goal") or (intent_record.summary if intent_record else (template.opencode_worker or {}).get("goal")))
        if policy_result.feedback:
            run_config["planner_feedback"] = list(policy_result.feedback)

        factory_run = FactoryRun(
            idea_id=project.idea_id,
            template_id=template.template_id,
            status="queued",
            config=dict(run_config),
            intent_id=intent_record.id if intent_record else None,
            run_type="intent_driven" if intent_record else config.get("run_type", "standard"),
            correlation_id=str(intent_record.correlation_id or config.get("correlation_id") or "") if intent_record else str(config.get("correlation_id") or ""),
            dedupe_hash=self._stable_hash({
                "idea_id": project.idea_id,
                "project_id": project_id,
                "template_id": template.template_id,
                "template_version": template.version,
                "intent_id": intent_record.id if intent_record else None,
                "goal": run_config.get("goal"),
                "run_type": "intent_driven" if intent_record else config.get("run_type", "standard"),
            }),
            budget=dict(intent_record.budget if intent_record else config.get("budget") or {}),
            stop_conditions=list(intent_record.stop_conditions if intent_record else config.get("stop_conditions") or []),
        )
        if not factory_run.config.get("ledger_path"):
            default_ledger_path = f"karkhana-runs/{factory_run.id}.md"
            if Path(default_ledger_path).exists():
                factory_run.config["ledger_path"] = default_ledger_path
        role_contracts = await self._build_role_contracts(
            project=project,
            template=template,
            factory_run_id=factory_run.id,
            run_config=run_config,
            template_context=template_context,
        )
        factory_run.config["role_contracts"] = role_contracts
        if not factory_run.correlation_id:
            factory_run.correlation_id = f"factory-run:{factory_run.id}"
        factory_run.config["correlation_id"] = factory_run.correlation_id
        await repo.create_factory_run(factory_run)
        if intent_record:
            intent_record.correlation_id = intent_record.correlation_id or factory_run.correlation_id
            if factory_run.id not in intent_record.factory_run_ids:
                intent_record.factory_run_ids.append(factory_run.id)
            await repo.save_intent(intent_record)
            await self._emit_worker_event(
                repo,
                worker_id="system",
                event_type="intent_created",
                payload={
                    "intent_id": intent_record.id,
                    "summary": intent_record.summary,
                    "factory_run_id": factory_run.id,
                    "project_id": project_id,
                },
                factory_run_id=factory_run.id,
                correlation_id=factory_run.correlation_id,
                actor="system",
                idempotency_key=f"intent-created:{intent_record.id}",
            )
        await self._emit_worker_event(
            repo,
            worker_id="system",
            event_type="factory_run_created",
            payload={
                "factory_run_id": factory_run.id,
                "template_id": template.template_id,
                "project_id": project_id,
                "intent_id": intent_record.id if intent_record else None,
            },
            factory_run_id=factory_run.id,
            correlation_id=factory_run.correlation_id,
            actor="system",
            idempotency_key=f"factory-run-created:{factory_run.id}",
        )

        phases = await self._generate_phases(repo, factory_run, template)

        first_phase = phases[0] if phases else None
        first_batch: FactoryBatch | None = None
        work_item: WorkItem | None = None

        if first_phase:
            first_batch = await repo.save_factory_batch(FactoryBatch(
                factory_phase_id=first_phase.id,
                factory_run_id=factory_run.id,
                batch_key=f"{first_phase.phase_key}-batch-1",
            ))

            worker_contract = await self._build_worker_contract(
                project=project,
                template=template,
                factory_run=factory_run,
                phase=first_phase,
                batch=first_batch,
                template_context=template_context,
            )

            if can_enqueue_work(factory_run):
                work_item = await self._project_service.enqueue_job(
                    idea_id=project.idea_id,
                    project_id=project.id,
                    job_type=FACTORY_WORKER_JOB_TYPE,
                    payload=worker_contract,
                    idempotency_key=f"factory:{factory_run.id}:phase:{first_phase.phase_key}",
                    priority=60,
                    factory_run_id=factory_run.id,
                    rationale=intent_record.summary if intent_record else config.get("goal"),
                    correlation_id=factory_run.correlation_id,
                    dedupe_hash=self._stable_hash({
                        "factory_run_id": factory_run.id,
                        "phase_key": first_phase.phase_key,
                        "batch_key": first_batch.batch_key,
                    }),
                    budget=dict(factory_run.budget or {}),
                    stop_conditions=list(factory_run.stop_conditions or []),
                    branch_name=f"factory/{factory_run.id[:8]}/{first_phase.phase_key}",
                    ledger_path=(factory_run.config or {}).get("ledger_path"),
                    ledger_policy=(factory_run.config or {}).get("ledger_policy", "none"),
                )

                first_batch.work_item_id = work_item.id
                await repo.save_factory_batch(first_batch)

        if first_phase:
            factory_run.status = "running"
            await repo.save_factory_run(factory_run)
            first_phase.status = "running"
            first_phase.started_at = utcnow()
            await repo.save_factory_phase(first_phase)

        await refresh_factory_run_tracking_manifest(repo, factory_run.id)
        bundle = await collect_factory_run_bundle(repo, factory_run.id)
        if not bundle:
            raise ValueError("Factory run not found after creation")
        research_artifacts = await repo.list_research_artifacts(factory_run.id)
        review_packet = await repo.get_review_packet(factory_run.id)
        return {
            "factory_run": to_jsonable(bundle["factory_run"]),
            "phases": [to_jsonable(p) for p in bundle["phases"]],
            "first_batch": to_jsonable(first_batch) if first_batch else None,
            "work_item": to_jsonable(work_item) if work_item else None,
            "tracking_manifest": to_jsonable(bundle["tracking_manifest"]),
            "tracking_summary": bundle["tracking_summary"],
            "intent": to_jsonable(intent_record) if intent_record else None,
            "research_artifacts": [to_jsonable(artifact) for artifact in research_artifacts],
            "research_artifact_count": len(research_artifacts),
            "research_handoff": to_jsonable(review_packet) if review_packet and review_packet.packet_type == "research_handoff" else None,
            "factory_state": {
                "intent_summary": intent_record.summary if intent_record else factory_run.config.get("goal"),
                "correlation_id": factory_run.correlation_id or (intent_record.correlation_id if intent_record else None),
                "budget": factory_run.budget or (intent_record.budget if intent_record else {}),
                "stop_conditions": factory_run.stop_conditions or (intent_record.stop_conditions if intent_record else []),
                "research_artifact_count": len(research_artifacts),
                "handoff_status": review_packet.wait_window_state if review_packet and review_packet.packet_type == "research_handoff" else "not_created",
            },
        }

    async def get_factory_run(self, factory_run_id: str) -> dict[str, Any]:
        repo = get_repository()
        bundle = await collect_factory_run_bundle(repo, factory_run_id)
        if not bundle:
            raise ValueError("Factory run not found")
        factory_run: FactoryRun = bundle["factory_run"]
        intent = await repo.get_intent(factory_run.idea_id, factory_run.intent_id) if factory_run.intent_id else None
        research_artifacts = await repo.list_research_artifacts(factory_run_id)
        review_packet = await repo.get_review_packet(factory_run_id)
        return {
            "factory_run": to_jsonable(factory_run),
            "phases": [to_jsonable(p) for p in bundle["phases"]],
            "batches": [to_jsonable(b) for b in bundle["batches"]],
            "verifications": [to_jsonable(v) for v in bundle["verifications"]],
            "tracking_manifest": to_jsonable(bundle["tracking_manifest"]),
            "tracking_summary": bundle["tracking_summary"],
            "intent": to_jsonable(intent) if intent else None,
            "research_artifacts": [to_jsonable(artifact) for artifact in research_artifacts],
            "research_artifact_count": len(research_artifacts),
            "research_handoff": to_jsonable(review_packet) if review_packet and review_packet.packet_type == "research_handoff" else None,
            "factory_state": {
                "intent_summary": intent.summary if intent else factory_run.config.get("goal"),
                "correlation_id": factory_run.correlation_id or (intent.correlation_id if intent else None),
                "budget": factory_run.budget or (intent.budget if intent else {}),
                "stop_conditions": factory_run.stop_conditions or (intent.stop_conditions if intent else []),
                "research_artifact_count": len(research_artifacts),
                "handoff_status": review_packet.wait_window_state if review_packet and review_packet.packet_type == "research_handoff" else "not_created",
            },
        }

    async def list_factory_runs(self, project_id: str) -> dict[str, Any]:
        repo = get_repository()
        project = await repo.get_project_twin_by_id(project_id)
        if not project:
            raise ValueError("Project twin not found")
        runs = await repo.list_factory_runs(idea_id=project.idea_id)
        return {
            "factory_runs": [to_jsonable(r) for r in runs],
        }

    async def create_research_artifact(
        self,
        factory_run_id: str,
        *,
        title: str,
        source: str,
        raw_content: str | None = None,
        raw_content_uri: str | None = None,
        raw_metadata: dict[str, Any] | None = None,
        normalized: dict[str, Any] | None = None,
        force: bool = False,
        correlation_id: str | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        repo = get_repository()
        run = await repo.get_factory_run(factory_run_id)
        if not run:
            raise ValueError("Factory run not found")

        normalized_payload = dict(normalized or self._normalize_research_artifact(
            title=title,
            source=source,
            raw_content=raw_content,
            raw_content_uri=raw_content_uri,
            raw_metadata=raw_metadata or {},
        ))
        dedupe_hash = self._stable_hash({
            "factory_run_id": factory_run_id,
            "title": title,
            "source": source,
            "raw_content": raw_content or "",
            "raw_content_uri": raw_content_uri or "",
            "raw_metadata": raw_metadata or {},
            "normalized": normalized_payload,
        })

        if not force:
            existing = next(
                (artifact for artifact in await repo.list_research_artifacts(factory_run_id, statuses={"active"}) if artifact.dedupe_hash == dedupe_hash),
                None,
            )
            if existing:
                return {
                    "research_artifact": to_jsonable(existing),
                    "deduped": True,
                }

        metadata = ArtifactMetadata(
            source=source,
            source_uri=raw_content_uri,
            actor=actor,
            correlation_id=correlation_id or run.correlation_id,
            dedupe_hash=dedupe_hash,
            extra=dict(raw_metadata or {}),
        )
        artifact = ResearchArtifact(
            factory_run_id=factory_run_id,
            title=title,
            source=source,
            raw_content=raw_content,
            raw_content_uri=raw_content_uri,
            raw_metadata=dict(raw_metadata or {}),
            normalized=normalized_payload,
            artifact_metadata=metadata,
            dedupe_hash=dedupe_hash,
        )
        artifact = await repo.save_research_artifact(artifact)

        event_correlation_id = correlation_id or run.correlation_id or artifact.id
        await self._emit_worker_event(
            repo,
            worker_id="system",
            event_type="research_imported",
            payload={
                "research_artifact_id": artifact.id,
                "factory_run_id": factory_run_id,
                "title": title,
                "source": source,
                "dedupe_hash": dedupe_hash,
            },
            factory_run_id=factory_run_id,
            research_artifact_id=artifact.id,
            correlation_id=event_correlation_id,
            actor=actor,
            idempotency_key=f"research-imported:{artifact.id}",
        )
        await self._emit_worker_event(
            repo,
            worker_id="system",
            event_type="research_normalized",
            payload={
                "research_artifact_id": artifact.id,
                "normalized": normalized_payload,
            },
            factory_run_id=factory_run_id,
            research_artifact_id=artifact.id,
            correlation_id=event_correlation_id,
            actor=actor,
            idempotency_key=f"research-normalized:{artifact.id}",
        )

        return {
            "research_artifact": to_jsonable(artifact),
            "deduped": False,
        }

    async def _emit_worker_event(
        self,
        repo: Any,
        *,
        worker_id: str,
        event_type: str,
        payload: dict[str, Any],
        factory_run_id: str | None = None,
        research_artifact_id: str | None = None,
        review_packet_id: str | None = None,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
        actor: str | None = None,
        work_item_id: str | None = None,
    ) -> WorkerEvent:
        event = WorkerEvent(
            worker_id=worker_id,
            event_type=event_type,
            payload=payload,
            work_item_id=work_item_id,
            factory_run_id=factory_run_id,
            research_artifact_id=research_artifact_id,
            review_packet_id=review_packet_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            actor=actor,
        )
        await repo.add_worker_event(event)
        return event

    def _normalize_research_artifact(
        self,
        *,
        title: str,
        source: str,
        raw_content: str | None,
        raw_content_uri: str | None,
        raw_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        text = (raw_content or "").strip()
        summary = ""
        if text:
            summary = next((line.strip("-* \t") for line in text.splitlines() if line.strip()), "")
        if not summary:
            summary = title.strip() or source.strip()

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        key_points = [line.lstrip("-* ").strip() for line in lines if line.lstrip().startswith(("-", "*"))][:8]
        if not key_points and text:
            key_points = lines[:5]

        return {
            "title": title,
            "source": source,
            "summary": summary,
            "key_points": key_points,
            "word_count": len(text.split()) if text else 0,
            "raw_content_uri": raw_content_uri,
            "metadata": dict(raw_metadata or {}),
        }

    def _stable_hash(self, payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _normalize_path_guardrails(
        self,
        path_guardrails: dict[str, Any] | None,
        template_manifest: dict[str, Any] | None = None,
    ) -> dict[str, list[str]]:
        allowed_paths = list((path_guardrails or {}).get("allowed_paths") or (template_manifest or {}).get("allowed_paths") or [])
        forbidden_paths = list((path_guardrails or {}).get("forbidden_paths") or (template_manifest or {}).get("forbidden_paths") or [])
        if not allowed_paths:
            allowed_paths = ["backend/**", "frontend/**", "docs/**", "scripts/**", "tests/**"]
        if not forbidden_paths:
            forbidden_paths = [".karkhana/**"]
        return {
            "allowed_paths": allowed_paths,
            "forbidden_paths": forbidden_paths,
        }

    async def _generate_phases(
        self,
        repo: Any,
        factory_run: FactoryRun,
        template: TemplatePack,
    ) -> list[FactoryPhase]:
        template_phases = template.phases or []
        if not template_phases:
            template_phases = [{"key": "build", "label": "Build"}]

        phases: list[FactoryPhase] = []
        for idx, phase_def in enumerate(template_phases):
            phase = FactoryPhase(
                factory_run_id=factory_run.id,
                phase_key=phase_def.get("key", f"phase-{idx + 1}"),
                phase_order=idx + 1,
                status="pending",
                config_override=phase_def.get("config", {}),
            )
            await repo.save_factory_phase(phase)
            phases.append(phase)
        return phases

    def _initial_phase_key(self, template: TemplatePack) -> str:
        for phase in template.phases or []:
            key = str((phase or {}).get("key") or "").strip()
            if key:
                return key
        return "build"

    def _compact_artifact_ref(
        self,
        ref: dict[str, Any],
        *,
        doc_map: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        key = str(ref.get("key") or ref.get("artifact_key") or "").strip()
        doc = doc_map.get(key) if doc_map else None
        compact = {
            "key": key,
            "path": str(ref.get("path") or "").strip(),
            "kind": str(ref.get("kind") or "artifact").strip(),
            "description": str(ref.get("description") or "").strip(),
            "required": bool(ref.get("required", True)),
            "scope_path": ref.get("scope_path"),
            "storage_key": ref.get("storage_key"),
        }
        if doc:
            compact["uri"] = doc.get("uri")
            compact["content_type"] = doc.get("content_type")
        elif ref.get("uri"):
            compact["uri"] = ref.get("uri")
        if ref.get("content_type"):
            compact["content_type"] = ref.get("content_type")
        return {key: value for key, value in compact.items() if value not in (None, "", [], {})}

    def _compact_context_card(self, ref: dict[str, Any]) -> dict[str, Any]:
        compact = {
            "key": str(ref.get("key") or ref.get("artifact_key") or ref.get("path") or ref.get("uri") or "").strip(),
            "uri": str(ref.get("uri") or ref.get("storage_key") or "").strip(),
            "content_type": str(ref.get("content_type") or "text/markdown").strip(),
            "scope_path": ref.get("scope_path") or ref.get("path"),
            "kind": str(ref.get("kind") or ref.get("artifact_kind") or "context_card").strip(),
        }
        if ref.get("description"):
            compact["description"] = str(ref.get("description") or "").strip()
        if ref.get("version"):
            compact["version"] = str(ref.get("version") or "").strip()
        return {key: value for key, value in compact.items() if value not in (None, "", [], {})}

    def _derive_module_ids(self, project_blueprint: dict[str, Any], context_files: list[dict[str, str]], code_index: Any | None = None) -> list[str]:
        modules = _copy_list(project_blueprint.get("files_or_modules"))
        if modules:
            return list(dict.fromkeys(modules))

        fallback_paths = [entry.get("path", "") for entry in context_files if entry.get("path")]
        if not fallback_paths and code_index and getattr(code_index, "file_inventory", None):
            fallback_paths = [entry.get("path", "") for entry in (code_index.file_inventory or []) if entry.get("path")]

        derived: list[str] = []
        for path in fallback_paths:
            normalized = str(path or "").strip().strip("/")
            if not normalized or normalized == ".":
                continue
            if "/" in normalized:
                parts = [part for part in normalized.split("/") if part]
                if len(parts) >= 2:
                    derived.append("/".join(parts[:2]))
                else:
                    derived.append(parts[0])
            else:
                derived.append(normalized)
        return list(dict.fromkeys(derived))

    def _build_template_asset_refs(
        self,
        *,
        template_manifest: dict[str, Any],
        template_docs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        doc_map = {
            str(doc.get("key") or "").strip(): doc
            for doc in template_docs
            if str(doc.get("key") or "").strip()
        }
        assets = [
            self._compact_artifact_ref(ref, doc_map=doc_map)
            for ref in (template_manifest.get("artifacts") or [])
            if isinstance(ref, dict)
        ]
        if not assets:
            assets = [
                self._compact_context_card(doc)
                for doc in template_docs
            ]
        return [asset for asset in assets if asset]

    def _build_context_cards(
        self,
        *,
        template_docs: list[dict[str, Any]],
        resolved_agents_hierarchy: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        source_cards = resolved_agents_hierarchy or template_docs
        cards = [self._compact_context_card(ref) for ref in source_cards if isinstance(ref, dict)]
        return [card for card in cards if card]

    def _derive_files_likely_needed(
        self,
        *,
        context_files: list[dict[str, str]],
        template_assets: list[dict[str, Any]],
        template_manifest: dict[str, Any],
    ) -> list[str]:
        files = [str(entry.get("path") or "").strip() for entry in context_files if str(entry.get("path") or "").strip()]
        if not files:
            files = ["graphify-out/GRAPH_REPORT.md"]
            files.extend(
                str(asset.get("path") or "").strip()
                for asset in template_assets
                if str(asset.get("path") or "").strip()
            )
            files.extend(
                str(path).strip()
                for path in (template_manifest.get("allowed_paths") or [])[:3]
                if str(path).strip()
            )
        return list(dict.fromkeys(files))

    def _build_graph_context(
        self,
        *,
        project: ProjectTwin,
        template: TemplatePack,
        template_context: dict[str, Any] | None,
        template_manifest: dict[str, Any],
        code_index: Any | None,
        context_files: list[dict[str, str]],
        files_likely_needed: list[str],
    ) -> dict[str, Any]:
        graphify_expectations = dict((template_context or {}).get("graphify_expectations") or template_manifest.get("graphify_expectations") or {})
        graph_context: dict[str, Any] = {
            "report_path": "graphify-out/GRAPH_REPORT.md",
            "wiki_index_path": "graphify-out/wiki/index.md",
            "source": "code_index" if code_index else "template_defaults",
            "template_id": template.template_id,
            "template_version": template.version,
            "graphify_expectations": graphify_expectations,
            "files_likely_needed": files_likely_needed,
            "context_file_paths": [entry.get("path") for entry in context_files if entry.get("path")],
        }
        if code_index:
            graph_context.update({
                "commit_sha": getattr(code_index, "commit_sha", None),
                "architecture_summary": getattr(code_index, "architecture_summary", ""),
                "inventory_size": len(getattr(code_index, "file_inventory", []) or []),
                "manifest_count": len(getattr(code_index, "manifests", []) or []),
            })
        else:
            graph_context.update({
                "default_allowed_paths": list(template_manifest.get("allowed_paths") or []),
                "default_forbidden_paths": list(template_manifest.get("forbidden_paths") or []),
                "project_default_branch": project.default_branch,
            })
        return graph_context

    def _build_output_contract(self, output_schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "worker_output_contract.v1",
            "required_fields": list(output_schema.get("required") or []),
            "property_keys": list((output_schema.get("properties") or {}).keys()),
        }

    def _build_scaffold_manifest(
        self,
        *,
        factory_run_id: str,
        template: TemplatePack,
        project_blueprint: dict[str, Any],
        template_context: dict[str, Any] | None,
        code_index: Any | None,
        phase_key: str,
        batch_key: str,
        phase_id: str | None = None,
        batch_id: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        selected_assets: list[dict[str, Any]] | None = None,
        files_likely_needed: list[str] | None = None,
        files_forbidden: list[str] | None = None,
        module_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        template_manifest = dict((template_context or {}).get("template_manifest") or {})
        template_docs = []
        if template_context and template_context.get("resolved_agents"):
            template_docs = [ref for ref in template_context.get("resolved_agents") or [] if isinstance(ref, dict)]
        assets = selected_assets or self._build_template_asset_refs(
            template_manifest=template_manifest,
            template_docs=template_docs,
        )
        manifest = {
            "schema_version": "v1",
            "scaffold_mode": "planned",
            "factory_run_id": factory_run_id,
            "template_id": template.template_id,
            "template_version": template.version,
            "phase_key": phase_key,
            "batch_key": batch_key,
            "task_type": task_type or f"factory_phase:{phase_key}",
            "module_ids": module_ids or self._derive_module_ids(project_blueprint, [], code_index),
            "selected_assets": assets,
            "generated_files": [],
            "file_hashes": {},
            "files_likely_needed": files_likely_needed or self._derive_files_likely_needed(
                context_files=[],
                template_assets=assets,
                template_manifest=template_manifest,
            ),
            "files_forbidden": files_forbidden or self._normalize_path_guardrails(
                (template_context or {}).get("path_guardrails"),
                template_manifest,
            )["forbidden_paths"],
        }
        if phase_id:
            manifest["phase_id"] = phase_id
            manifest["factory_phase_id"] = phase_id
        if batch_id:
            manifest["batch_id"] = batch_id
            manifest["factory_batch_id"] = batch_id
        if task_id:
            manifest["task_id"] = task_id
        if code_index:
            manifest["graph_context"] = self._build_graph_context(
                project=ProjectTwin(
                    idea_id=str(project_blueprint.get("project_id") or ""),
                    provider=str(project_blueprint.get("provider") or ""),
                    installation_id=str(project_blueprint.get("installation_id") or ""),
                    owner=str(project_blueprint.get("owner") or ""),
                    repo=str(project_blueprint.get("repo") or ""),
                    repo_full_name=str(project_blueprint.get("repo_full_name") or ""),
                    repo_url=str(project_blueprint.get("repo_url") or ""),
                    clone_url=str(project_blueprint.get("clone_url") or ""),
                    default_branch=str(project_blueprint.get("default_branch") or "main"),
                ),
                template=template,
                template_context=template_context,
                template_manifest=template_manifest,
                code_index=code_index,
                context_files=[],
                files_likely_needed=manifest["files_likely_needed"],
            )
        else:
            manifest["graph_context"] = self._build_graph_context(
                project=ProjectTwin(
                    idea_id=str(project_blueprint.get("project_id") or ""),
                    provider=str(project_blueprint.get("provider") or ""),
                    installation_id=str(project_blueprint.get("installation_id") or ""),
                    owner=str(project_blueprint.get("owner") or ""),
                    repo=str(project_blueprint.get("repo") or ""),
                    repo_full_name=str(project_blueprint.get("repo_full_name") or ""),
                    repo_url=str(project_blueprint.get("repo_url") or ""),
                    clone_url=str(project_blueprint.get("clone_url") or ""),
                    default_branch=str(project_blueprint.get("default_branch") or "main"),
                ),
                template=template,
                template_context=template_context,
                template_manifest=template_manifest,
                code_index=None,
                context_files=[],
                files_likely_needed=manifest["files_likely_needed"],
            )
        manifest["duplicate_work_key"] = self._stable_hash({
            "factory_run_id": factory_run_id,
            "phase_id": phase_id or "",
            "batch_id": batch_id or "",
            "task_id": task_id or "",
            "task_type": manifest["task_type"],
            "template_id": template.template_id,
            "template_version": template.version,
            "module_ids": manifest["module_ids"],
            "files_likely_needed": manifest["files_likely_needed"],
            "files_forbidden": manifest["files_forbidden"],
            "selected_assets": [
                asset.get("key") or asset.get("path") or asset.get("uri") or ""
                for asset in assets
            ],
        })
        return manifest

    def _build_worker_context_bundle(
        self,
        *,
        project: ProjectTwin,
        template: TemplatePack,
        factory_run: FactoryRun,
        phase: FactoryPhase,
        batch: FactoryBatch,
        template_context: dict[str, Any] | None,
        code_index: Any | None,
        context_files: list[dict[str, str]],
        template_docs: list[dict[str, Any]],
        role_output_schema: dict[str, Any],
        verification_commands: list[str],
        project_blueprint: dict[str, Any],
        template_manifest: dict[str, Any],
        resolved_agents_hierarchy: list[dict[str, Any]],
        graphify_instructions: dict[str, list[str]],
        task_type: str,
        goal: str,
    ) -> dict[str, Any]:
        template_assets = self._build_template_asset_refs(
            template_manifest=template_manifest,
            template_docs=template_docs,
        )
        likely_files = self._derive_files_likely_needed(
            context_files=context_files,
            template_assets=template_assets,
            template_manifest=template_manifest,
        )
        files_forbidden = self._normalize_path_guardrails((factory_run.config or {}).get("path_guardrails"), template_manifest)["forbidden_paths"]
        module_ids = self._derive_module_ids(project_blueprint, context_files, code_index)
        context_cards = self._build_context_cards(
            template_docs=template_docs,
            resolved_agents_hierarchy=resolved_agents_hierarchy,
        )
        graph_context = self._build_graph_context(
            project=project,
            template=template,
            template_context=template_context,
            template_manifest=template_manifest,
            code_index=code_index,
            context_files=context_files,
            files_likely_needed=likely_files,
        )
        output_contract = self._build_output_contract(role_output_schema)
        bundle = {
            "schema_version": "v1",
            "task_id": batch.id,
            "factory_run_id": factory_run.id,
            "phase_id": phase.id,
            "factory_phase_id": phase.id,
            "phase_key": phase.phase_key,
            "batch_id": batch.id,
            "factory_batch_id": batch.id,
            "batch_key": batch.batch_key,
            "template_id": template.template_id,
            "template_version": template.version,
            "module_ids": module_ids,
            "task_type": task_type,
            "graph_context": graph_context,
            "files_likely_needed": likely_files,
            "files_forbidden": files_forbidden,
            "context_cards": context_cards,
            "template_assets": template_assets,
            "verification_commands": list(verification_commands),
            "output_contract": output_contract,
            "duplicate_work_key": self._stable_hash({
                "task_id": batch.id,
                "factory_run_id": factory_run.id,
                "phase_id": phase.id,
                "batch_id": batch.id,
                "phase_key": phase.phase_key,
                "batch_key": batch.batch_key,
                "template_id": template.template_id,
                "template_version": template.version,
                "module_ids": module_ids,
                "files_likely_needed": likely_files,
                "files_forbidden": files_forbidden,
                "verification_commands": list(verification_commands),
                "task_type": task_type,
            }),
        }
        ledger_path = (factory_run.config or {}).get("ledger_path")
        bundle["ledger_path"] = ledger_path
        bundle["ledger_policy"] = (factory_run.config or {}).get("ledger_policy", "none")
        bundle["ledger_context"] = extract_compact_ledger_context(ledger_path)
        scaffold_manifest = self._build_scaffold_manifest(
            factory_run_id=factory_run.id,
            template=template,
            project_blueprint=project_blueprint,
            template_context=template_context,
            code_index=code_index,
            phase_key=phase.phase_key,
            batch_key=batch.batch_key,
            phase_id=phase.id,
            batch_id=batch.id,
            task_id=batch.id,
            task_type=task_type,
            selected_assets=template_assets,
            files_likely_needed=likely_files,
            files_forbidden=files_forbidden,
            module_ids=module_ids,
        )
        bundle["scaffold_manifest"] = scaffold_manifest
        return bundle

    async def _build_worker_contract(
        self,
        project: ProjectTwin,
        template: TemplatePack,
        factory_run: FactoryRun,
        phase: FactoryPhase,
        batch: FactoryBatch,
        template_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repo = get_repository()
        template_docs = await self._collect_template_docs(repo, template.template_id)
        code_index = await repo.get_latest_code_index(project.idea_id)
        intent = await repo.get_intent(project.idea_id, factory_run.intent_id) if factory_run.intent_id else None
        project_blueprint = dict((factory_run.config or {}).get("project_blueprint") or {})
        permission_profile = project_blueprint.get("permission_profile") or {}
        policy_result = (factory_run.config or {}).get("policy_result") or {}
        template_manifest = dict((factory_run.config or {}).get("template_manifest") or (template_context or {}).get("template_manifest") or {})
        verification_expectations = list((factory_run.config or {}).get("verification_commands") or template_manifest.get("verification_commands") or [])
        graphify_expectations = dict((factory_run.config or {}).get("graphify_expectations") or template_manifest.get("graphify_expectations") or {})
        path_guardrails = self._normalize_path_guardrails((factory_run.config or {}).get("path_guardrails"), template_manifest)
        resolved_agents_hierarchy = list((factory_run.config or {}).get("resolved_agents_hierarchy") or (template_context or {}).get("resolved_agents") or [])

        constraints = template.constraints or []
        opencode_worker = template.opencode_worker or {}
        quality_gates = template.quality_gates or []
        required_capabilities = project_blueprint.get("required_capabilities") or []

        branch_name = f"factory/{factory_run.id[:8]}/{phase.phase_key}"

        context_files: list[dict[str, str]] = []
        if code_index:
            for entry in (code_index.file_inventory or [])[:20]:
                context_files.append({"path": entry.get("path", ""), "role": "source"})
            if code_index.architecture_summary:
                context_files.append({
                    "path": "graphify-out/GRAPH_REPORT.md",
                    "role": "architecture_context",
                })

        deliverables = opencode_worker.get("deliverables", [
            "Implementation of the phase goal",
            "Passing test suite",
            "Updated graphify knowledge graph",
        ])

        verification_commands = opencode_worker.get("verification_commands", [])
        if not verification_commands:
            for cmd in (project.test_commands or []):
                verification_commands.append(cmd)
        if "graphify update ." not in verification_commands:
            verification_commands.append("graphify update .")

        graphify_instructions = project_blueprint.get("graphify_requirements") or {
            "pre_task": [
                "Read graphify-out/GRAPH_REPORT.md for god nodes and community structure",
                "Read graphify-out/wiki/index.md if it exists for codebase navigation",
            ],
            "post_task": [
                "Run 'graphify update .' after all code changes to keep the knowledge graph current",
            ],
        }
        worker_context_bundle = self._build_worker_context_bundle(
            project=project,
            template=template,
            factory_run=factory_run,
            phase=phase,
            batch=batch,
            template_context=template_context,
            code_index=code_index,
            context_files=context_files,
            template_docs=template_docs,
            role_output_schema=RolePromptBuilder.definition(FactoryRole.WORKER).output_schema,
            verification_commands=verification_commands,
            project_blueprint=project_blueprint,
            template_manifest=template_manifest,
            resolved_agents_hierarchy=resolved_agents_hierarchy,
            graphify_instructions=graphify_instructions,
            task_type=f"factory_phase:{phase.phase_key}",
            goal=opencode_worker.get("goal") or f"Execute factory phase '{phase.phase_key}' for project {project.repo_full_name}",
        )
        output_contract = worker_context_bundle["output_contract"]
        scaffold_manifest = worker_context_bundle["scaffold_manifest"]
        role_context = {
            "project": to_jsonable(project),
            "template": to_jsonable(template),
            "factory_run_id": factory_run.id,
            "phase": to_jsonable(phase),
            "batch": to_jsonable(batch),
            "branch_name": branch_name,
            "phase_key": phase.phase_key,
            "project_repo_full_name": project.repo_full_name,
            "context_files": context_files,
            "constraints": constraints,
            "quality_gates": quality_gates,
            "deliverables": deliverables,
            "verification_commands": verification_commands,
            "graphify_instructions": graphify_instructions,
            "ledger_context": worker_context_bundle.get("ledger_context") or {},
            "template_manifest": template_manifest,
            "template_version": template.version,
            "template_id": template.template_id,
            "verification_expectations": verification_expectations,
            "graphify_expectations": graphify_expectations,
            "path_guardrails": path_guardrails,
            "resolved_agents_hierarchy": resolved_agents_hierarchy,
            "intent": to_jsonable(intent) if intent else {},
            "intent_summary": intent.summary if intent else (factory_run.config or {}).get("goal", ""),
            "budget": dict(factory_run.budget or {}),
            "stop_conditions": list(factory_run.stop_conditions or []),
            "goal": opencode_worker.get("goal") or f"Execute factory phase '{phase.phase_key}' for project {project.repo_full_name}",
            "worker_context_bundle": worker_context_bundle,
            "output_contract": output_contract,
            "scaffold_manifest": scaffold_manifest,
        }
        role_prompt = RolePromptBuilder.build(FactoryRole.WORKER, role_context)
        verifier_contract = RolePromptBuilder.build(
            FactoryRole.VERIFIER,
            {
                "project": to_jsonable(project),
                "factory_run_id": factory_run.id,
                "factory_batch_id": batch.id,
                "verification_commands": verification_commands,
                "expected_result_fields": list(role_prompt["output_schema"].get("properties", {}).keys()),
            },
        )

        return {
            "goal": opencode_worker.get("goal") or f"Execute factory phase '{phase.phase_key}' for project {project.repo_full_name}",
            "role": role_prompt["role"],
            "role_prompt": role_prompt["prompt"],
            "role_prompt_template": role_prompt["prompt_template"],
            "role_required_inputs": role_prompt["required_inputs"],
            "role_output_schema": role_prompt["output_schema"],
            "role_provider": role_prompt["provider"],
            "role_model": role_prompt["model"],
            "messages": role_prompt["messages"],
            "prompt": role_prompt["prompt"],
            "task_id": batch.id,
            "task_type": f"factory_phase:{phase.phase_key}",
            "factory_run_id": factory_run.id,
            "factory_phase_id": phase.id,
            "factory_batch_id": batch.id,
            "factory_job_type": f"factory_phase:{phase.phase_key}",
            "execution_type": FACTORY_WORKER_JOB_TYPE,
            "autonomy_level": (factory_run.config or {}).get("autonomy_level", AUTONOMY_AUTONOMOUS_DEVELOPMENT),
            "guardrails": [
                "Never silently deploy to production",
                "Never add paid services or subscriptions",
                "Never commit secrets, API keys, or credentials",
                "Never run destructive database changes (DROP TABLE, DELETE without WHERE, etc.)",
            ],
            "project_twin": {
                "project_id": project.id,
                "idea_id": project.idea_id,
                "provider": project.provider,
                "owner": project.owner,
                "repo": project.repo,
                "repo_full_name": project.repo_full_name,
                "clone_url": project.clone_url,
                "default_branch": project.default_branch,
                "detected_stack": project.detected_stack,
            },
            "branch": branch_name,
            "base_branch": project.default_branch,
            "context_files": context_files,
            "template_docs": template_docs,
            "template_version": template.version,
            "template_id": template.template_id,
            "project_blueprint": project_blueprint,
            "permission_profile": permission_profile,
            "required_capabilities": required_capabilities,
            "policy_result": policy_result,
            "constraints": constraints,
            "quality_gates": quality_gates,
            "deliverables": deliverables,
            "verification_commands": verification_commands,
            "graphify_instructions": graphify_instructions,
            "template_manifest": template_manifest,
            "verification_expectations": verification_expectations,
            "graphify_expectations": graphify_expectations,
            "path_guardrails": path_guardrails,
            "resolved_agents_hierarchy": resolved_agents_hierarchy,
            "response_schema": role_prompt["output_schema"],
            "output_contract": output_contract,
            "worker_context_bundle": worker_context_bundle,
            "scaffold_manifest": scaffold_manifest,
            "verifier_contract": verifier_contract,
        }

    async def _collect_template_docs(self, repo: Any, template_id: str) -> list[dict[str, str]]:
        artifacts = await repo.list_template_artifacts(template_id)
        # Auto-import AGENTS.md if not yet stored for this template pack
        has_agents_md = any(
            a.artifact_key == "AGENTS.md" or a.artifact_key.startswith("AGENTS.md#")
            for a in artifacts
        )
        if not has_agents_md:
            try:
                await AgentsMdArtifactService(repo=repo).import_from_disk(template_id=template_id)
                artifacts = await repo.list_template_artifacts(template_id)
            except Exception:
                pass
        docs: list[dict[str, str]] = []
        for artifact in artifacts:
            if artifact.content_type in ("text/markdown", "text/plain", "application/json"):
                key = artifact.artifact_key
                if key.startswith("AGENTS.md#"):
                    key = "AGENTS.md"
                elif key.startswith("AGENTS.override.md#"):
                    key = "AGENTS.override.md"
                docs.append({
                    "key": key,
                    "uri": artifact.uri,
                    "content_type": artifact.content_type,
                    "content": artifact.content,
                    "version": artifact.version,
                    "compatibility": artifact.compatibility,
                })
        return docs

    async def _build_role_contracts(
        self,
        *,
        project: ProjectTwin,
        template: TemplatePack,
        factory_run_id: str,
        run_config: dict[str, Any],
        template_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repo = get_repository()
        template_docs = await self._collect_template_docs(repo, template.template_id)
        code_index = await repo.get_latest_code_index(project.idea_id)
        intent_id = run_config.get("intent_id")
        intent = await repo.get_intent(project.idea_id, intent_id) if intent_id else None
        code_context = {
            "template_docs": template_docs,
            "code_index": to_jsonable(code_index) if code_index else {},
            "constraints": template.constraints or [],
            "quality_gates": template.quality_gates or [],
            "template_manifest": (template_context or {}).get("template_manifest") or {},
            "verification_commands": (template_context or {}).get("verification_commands") or [],
            "graphify_expectations": (template_context or {}).get("graphify_expectations") or {},
            "path_guardrails": self._normalize_path_guardrails((template_context or {}).get("path_guardrails"), (template_context or {}).get("template_manifest") or {}),
        }
        research_context = {
            "project_description": project.desired_outcome or project.current_status or "",
            "detected_stack": project.detected_stack,
            "test_commands": project.test_commands,
            "intent_summary": intent.summary if intent else (run_config.get("goal") or ""),
            "budget": dict(run_config.get("budget") or {}),
            "stop_conditions": list(run_config.get("stop_conditions") or []),
        }
        phase_blueprints = [
            {
                "phase_key": phase.get("key", ""),
                "label": phase.get("label", ""),
                "config": phase.get("config", {}),
            }
            for phase in (template.phases or [])
        ]
        planner = RolePromptBuilder.build(
            FactoryRole.PLANNER,
            {
                "project": to_jsonable(project),
                "template": to_jsonable(template),
                "factory_run_id": factory_run_id or "<pending>",
                "run_config": run_config,
                "code_context": code_context,
                "research_context": research_context,
            },
        )
        batch_planner = RolePromptBuilder.build(
            FactoryRole.BATCH_PLANNER,
            {
                "project": to_jsonable(project),
                "template": to_jsonable(template),
                "factory_run_id": factory_run_id or "<pending>",
                "run_config": run_config,
                "phase_blueprints": phase_blueprints,
                "code_context": code_context,
                "research_context": research_context,
            },
        )
        return {
            "planner": planner,
            "batch_planner": batch_planner,
        }

    async def _build_project_blueprint(
        self,
        *,
        project: ProjectTwin,
        template: TemplatePack,
        config: dict[str, Any],
        template_context: dict[str, Any] | None = None,
    ) -> ProjectBlueprint:
        repo = get_repository()
        code_index = await repo.get_latest_code_index(project.idea_id)
        blueprint_raw = config.get("blueprint")
        blueprint_config = blueprint_raw if isinstance(blueprint_raw, dict) else {}

        build_steps = blueprint_config["build_steps"] if "build_steps" in blueprint_config else self._derive_build_steps(template)
        verification_commands = (
            blueprint_config["verification_commands"]
            if "verification_commands" in blueprint_config
            else self._derive_verification_commands(project=project, template=template, template_context=template_context)
        )
        required_capabilities = (
            blueprint_config["required_capabilities"]
            if "required_capabilities" in blueprint_config
            else self._derive_required_capabilities(
                template=template,
                build_steps=build_steps,
                verification_commands=verification_commands,
                blueprint_config=blueprint_config,
            )
        )

        blueprint_kwargs: dict[str, Any] = {
            "blueprint_id": blueprint_config["blueprint_id"] if "blueprint_id" in blueprint_config else f"{project.id}:{template.template_id}:{template.version}",
            "project_id": blueprint_config["project_id"] if "project_id" in blueprint_config else project.id,
            "template_id": blueprint_config["template_id"] if "template_id" in blueprint_config else template.template_id,
            "template_version": blueprint_config["template_version"] if "template_version" in blueprint_config else template.version,
            "target_stack": blueprint_config["target_stack"] if "target_stack" in blueprint_config else self._derive_target_stack(project, template),
            "files_or_modules": blueprint_config["files_or_modules"] if "files_or_modules" in blueprint_config else self._derive_files_or_modules(
                project=project,
                code_index=code_index,
            ),
            "dependencies": blueprint_config["dependencies"] if "dependencies" in blueprint_config else self._derive_dependencies(template, blueprint_config),
            "build_steps": build_steps,
            "verification_commands": verification_commands,
            "required_capabilities": required_capabilities,
            "graphify_requirements": blueprint_config["graphify_requirements"] if "graphify_requirements" in blueprint_config else self._derive_graphify_requirements(template_context),
        }
        if "permission_profile" in blueprint_config:
            blueprint_kwargs["permission_profile"] = blueprint_config["permission_profile"]
        else:
            blueprint_kwargs["permission_profile"] = self._build_permission_profile(
                blueprint_config=blueprint_config,
                build_steps=blueprint_kwargs["build_steps"],
                verification_commands=blueprint_kwargs["verification_commands"],
                required_capabilities=blueprint_kwargs["required_capabilities"],
            )
        if "created_at" in blueprint_config:
            blueprint_kwargs["created_at"] = blueprint_config["created_at"]

        permission_profile = blueprint_kwargs["permission_profile"]
        if isinstance(permission_profile, dict):
            blueprint_kwargs["permission_profile"] = WorkerPermissionProfile.from_dict(permission_profile)

        return ProjectBlueprint(**blueprint_kwargs)

    def _derive_target_stack(self, project: ProjectTwin, template: TemplatePack) -> list[str]:
        target_stack = _copy_list(project.detected_stack)
        if target_stack:
            return target_stack
        default_stack = template.default_stack or {}
        if isinstance(default_stack, dict):
            for key in ("stack", "target_stack", "framework", "runtime"):
                value = default_stack.get(key)
                if isinstance(value, list):
                    stack = _copy_list(value)
                    if stack:
                        return stack
                elif isinstance(value, str) and value.strip():
                    return [value.strip()]
        return []

    def _derive_files_or_modules(self, *, project: ProjectTwin, code_index: Any) -> list[str]:
        if code_index and getattr(code_index, "file_inventory", None):
            return [
                entry.get("path", "")
                for entry in (code_index.file_inventory or [])[:20]
                if entry.get("path")
            ]
        return []

    def _derive_dependencies(self, template: TemplatePack, blueprint_config: dict[str, Any]) -> list[str]:
        dependencies = _copy_list(blueprint_config.get("dependencies"))
        if dependencies:
            return dependencies
        template_dependencies = template.opencode_worker.get("dependencies") if template.opencode_worker else None
        if isinstance(template_dependencies, list):
            return [str(item) for item in template_dependencies if str(item).strip()]
        return []

    def _derive_build_steps(self, template: TemplatePack) -> list[str]:
        steps: list[str] = []
        for phase in template.phases or []:
            label = phase.get("label") or phase.get("key")
            if label:
                steps.append(f"Complete phase: {label}")
        goal = (template.opencode_worker or {}).get("goal")
        if goal:
            steps.append(str(goal))
        if not steps:
            steps.append(f"Execute template {template.template_id}")
        return steps

    def _derive_verification_commands(self, *, project: ProjectTwin, template: TemplatePack, template_context: dict[str, Any] | None = None) -> list[str]:
        verification_commands = _copy_list((template_context or {}).get("verification_commands"))
        if not verification_commands:
            verification_commands = _copy_list((template.opencode_worker or {}).get("verification_commands"))
        if not verification_commands:
            verification_commands = _copy_list(project.test_commands)
        if "graphify update ." not in verification_commands:
            verification_commands.append("graphify update .")
        return verification_commands

    def _derive_required_capabilities(
        self,
        *,
        template: TemplatePack,
        build_steps: list[str],
        verification_commands: list[str],
        blueprint_config: dict[str, Any],
    ) -> list[str]:
        required = [
            "agent_branch_work",
            "test_verify",
        ]
        template_required = blueprint_config.get("required_capabilities") or []
        if isinstance(template_required, list):
            required.extend([str(item) for item in template_required if str(item).strip()])
        opencode_required = (template.opencode_worker or {}).get("required_capabilities") or []
        if isinstance(opencode_required, list):
            required.extend([str(item) for item in opencode_required if str(item).strip()])
        return list(dict.fromkeys(required))

    def _build_permission_profile(
        self,
        *,
        blueprint_config: dict[str, Any],
        build_steps: list[str],
        verification_commands: list[str],
        required_capabilities: list[str],
    ) -> WorkerPermissionProfile:
        readonly_capabilities = {"repo_index", "architecture_dossier", "gap_analysis", "build_task_plan"}
        scoped_capabilities = readonly_capabilities | {
            "agent_branch_work",
            "test_verify",
            "graphify_update",
            "graphify_read",
            "file_edit_scoped",
            "shell_scoped",
            "sync_remote_state",
        }
        raw_profile = blueprint_config.get("permission_profile")
        if isinstance(raw_profile, WorkerPermissionProfile):
            return raw_profile
        if isinstance(raw_profile, dict) and raw_profile:
            return WorkerPermissionProfile.from_dict(raw_profile)

        if self._uses_high_risk_action(build_steps, verification_commands):
            ring = RING_3_HIGH_RISK_APPROVAL
        elif all(cap in readonly_capabilities for cap in required_capabilities):
            ring = RING_0_READONLY
        elif any(cap not in scoped_capabilities for cap in required_capabilities):
            ring = RING_2_TOOL_INTEGRATION
        else:
            ring = RING_1_SCOPED_EXECUTION

        allowed_capabilities = [cap for cap in required_capabilities if cap in KNOWN_WORKER_CAPABILITIES]
        tool_integrations = [
            cap for cap in required_capabilities if cap not in KNOWN_WORKER_CAPABILITIES and cap != "high_risk_approval"
        ]
        notes = [
            "Ring 0: readonly inspection",
            "Ring 1: scoped execution",
            "Ring 2: declared tool integrations",
            "Ring 3: high-risk approval required",
        ]
        return WorkerPermissionProfile(
            ring=ring,
            allowed_capabilities=allowed_capabilities,
            tool_integrations=tool_integrations,
            notes=notes,
        )

    def _derive_graphify_requirements(self, template_context: dict[str, Any] | None = None) -> dict[str, Any]:
        graphify_expectations = (template_context or {}).get("graphify_expectations") or {}
        if graphify_expectations:
            return graphify_expectations
        return {
            "pre_task": [
                "Read graphify-out/GRAPH_REPORT.md for god nodes and community structure",
                "Read graphify-out/wiki/index.md if it exists for codebase navigation",
            ],
            "post_task": [
                "Run 'graphify update .' after all code changes to keep the knowledge graph current",
            ],
        }

    @staticmethod
    def _uses_high_risk_action(build_steps: list[str], verification_commands: list[str]) -> bool:
        risky_patterns = (
            "deploy production",
            "production deploy",
            "deploy to production",
            "secret",
            "api key",
            "credential",
            "drop table",
            "delete from",
            "truncate",
            "rm -rf",
            "kubectl delete",
            "aws s3 rm",
            "git push --force",
            "force push",
            "broad shell",
            "unrestricted shell",
        )
        for command in [*build_steps, *verification_commands]:
            lowered = command.lower()
            if any(pattern in lowered for pattern in risky_patterns):
                return True
        return False


def _copy_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]
