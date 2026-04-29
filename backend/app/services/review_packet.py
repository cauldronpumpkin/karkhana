from __future__ import annotations

from typing import Any

from backend.app.repository import (
    IMPACT_SCORES,
    WAIT_WINDOW_STATES,
    FactoryRun,
    Intent,
    ResearchArtifact,
    LocalWorker,
    RepairTask,
    ReviewPacket,
    VerificationRun,
    WorkerEvent,
    get_repository,
    utcnow,
)
from backend.app.services.expert_council import ExpertCouncilService
from backend.app.services.factory_tracking import FACTORY_WORKER_JOB_TYPE, collect_factory_run_bundle
from backend.app.services.policy_engine import PolicyBlockedError, ProjectBlueprint, PythonPolicyEngine
from backend.app.services.project_twin import ProjectTwinService, to_jsonable
from backend.app.services.template_pack import TemplatePackService


VALID_TRANSITIONS: dict[str, set[str]] = {
    "awaiting_review": {"wait_window", "approved", "rejected", "modification_requested", "paused"},
    "wait_window": {"no_objection_recorded", "ready_to_continue", "approved", "rejected", "modification_requested", "paused"},
    "no_objection_recorded": {"ready_to_continue", "approved", "rejected", "paused"},
    "ready_to_continue": {"approved", "rejected", "paused"},
    "approved": set(),
    "rejected": set(),
    "modification_requested": {"awaiting_review", "paused"},
    "paused": {"awaiting_review", "wait_window"},
}


class InvalidTransitionError(ValueError):
    pass


class ReviewPacketService:
    def __init__(self) -> None:
        self._project_service = ProjectTwinService()
        self._policy_engine = PythonPolicyEngine()
        self._expert_council = ExpertCouncilService()

    async def create_review_packet(self, factory_run_id: str) -> dict[str, Any]:
        repo = get_repository()
        template_service = TemplatePackService(repo=repo)
        bundle = await collect_factory_run_bundle(repo, factory_run_id)
        if not bundle:
            raise ValueError("Factory run not found")

        run: FactoryRun = bundle["factory_run"]
        existing = await repo.get_review_packet(factory_run_id)
        if existing:
            return to_jsonable(existing)

        config = run.config or {}
        template_manifest = dict(config.get("template_manifest") or {})
        if not template_manifest:
            fetched = await template_service.get_template_manifest(run.template_id)
            template_manifest = dict(fetched or {})
        verification_expectations = list(config.get("verification_commands") or template_manifest.get("verification_commands") or [])
        graphify_expectations = dict(config.get("graphify_expectations") or template_manifest.get("graphify_expectations") or {})
        path_guardrails = dict(config.get("path_guardrails") or {
            "allowed_paths": list(template_manifest.get("allowed_paths") or []),
            "forbidden_paths": list(template_manifest.get("forbidden_paths") or []),
        })
        batches = bundle["batches"]
        verifications: list[VerificationRun] = bundle["verifications"]
        repair_tasks: list[RepairTask] = bundle.get("repair_tasks", [])
        work_items = bundle.get("work_items", [])

        worker_id = None
        worker_display_name = None
        worker_machine_name = None
        for batch in batches:
            if batch.worker_id:
                worker_id = batch.worker_id
                break
        if worker_id:
            worker = await repo.get_local_worker(worker_id)
            if worker:
                worker_display_name = worker.display_name
                worker_machine_name = worker.machine_name

        branch_name = None
        for item in work_items:
            payload = item.payload or {}
            if payload.get("branch"):
                branch_name = payload["branch"]
                break

        blast_radius = self._compute_blast_radius(verifications, repair_tasks, work_items)
        execution_trace = self._compute_execution_trace(batches, verifications, repair_tasks, work_items)
        changed_files = self._collect_changed_files(verifications, repair_tasks)
        diff_summary_uri = self._compute_diff_uri(run, changed_files)

        tracking_manifest = bundle.get("tracking_manifest")
        graphify_updated = bool(config.get("graphify_updated"))
        if not graphify_updated:
            graphify_updated = any(bool((item.result or {}).get("graphify_updated")) for item in work_items)
        if not graphify_updated and tracking_manifest and getattr(tracking_manifest, "graphify_status", None) == "updated":
            graphify_updated = True
        guardrail_result = await template_service.validate_factory_run_guardrails(
            run.template_id,
            changed_files=changed_files,
            verification_commands=verification_expectations,
            graphify_updated=graphify_updated,
            mode="normal",
            completed=run.status in {"approved", "completed"},
        )
        safety_net = self._compute_safety_net(
            verifications,
            repair_tasks,
            tracking_manifest,
            template_id=run.template_id,
            template_version=config.get("template_version") or template_manifest.get("version"),
            verification_expectations=verification_expectations,
            graphify_expectations=graphify_expectations,
            path_guardrails=path_guardrails,
            guardrail_result=guardrail_result,
        )
        evaluator_verdict = self._compute_evaluator_verdict(verifications, safety_net)

        allowed_actions = self._compute_allowed_actions("awaiting_review")

        expert_policy = config.get("expert_policy") or template_manifest.get("expert_policy")
        expert_decisions, council_summary = self._expert_council.run_expert_reviews(
            changed_files=changed_files,
            safety_net=safety_net,
            blast_radius=blast_radius,
            decision_gates={
                "autonomy_level": config.get("autonomy_level"),
                "policy_result": config.get("policy_result"),
                "template_id": run.template_id,
                "template_version": config.get("template_version") or template_manifest.get("version"),
                "verification_expectations": verification_expectations,
                "graphify_expectations": graphify_expectations,
                "path_guardrails": path_guardrails,
                "guardrail_pass": safety_net.get("guardrail_pass"),
            },
            expert_policy=expert_policy,
        )

        packet = ReviewPacket(
            run_id=factory_run_id,
            promise=config.get("goal", config.get("opencode_worker", {}).get("goal", "")),
            packet_type="standard",
            status=run.status,
            wait_window_state="awaiting_review",
            branch_name=branch_name,
            worker_id=worker_id,
            worker_display_name=worker_display_name,
            worker_machine_name=worker_machine_name,
            autonomy_level=config.get("autonomy_level"),
            template_id=run.template_id,
            template_version=config.get("template_version") or template_manifest.get("version"),
            blast_radius=blast_radius,
            safety_net_results=safety_net,
            execution_trace=execution_trace,
            changed_files=changed_files,
            diff_summary_uri=diff_summary_uri,
            evaluator_verdict=evaluator_verdict,
            decision_gates={
                "autonomy_level": config.get("autonomy_level"),
                "policy_result": config.get("policy_result"),
                "template_id": run.template_id,
                "template_version": config.get("template_version") or template_manifest.get("version"),
                "verification_expectations": verification_expectations,
                "graphify_expectations": graphify_expectations,
                "path_guardrails": path_guardrails,
                "guardrail_pass": safety_net.get("guardrail_pass"),
            },
            allowed_actions=allowed_actions,
            expert_reviews=[d.to_dict() for d in expert_decisions],
            council_summary=council_summary.to_dict(),
            telemetry_events=[
                {"event_type": "review_packet_created", "timestamp": utcnow().isoformat()},
            ],
        )

        await repo.save_review_packet(packet)
        return to_jsonable(packet)

    async def create_research_handoff(self, factory_run_id: str) -> dict[str, Any]:
        repo = get_repository()
        bundle = await collect_factory_run_bundle(repo, factory_run_id)
        if not bundle:
            raise ValueError("Factory run not found")

        run: FactoryRun = bundle["factory_run"]
        existing = await repo.get_review_packet(factory_run_id)
        if existing and existing.packet_type == "research_handoff":
            return to_jsonable(existing)

        intent = await repo.get_intent(run.idea_id, run.intent_id) if run.intent_id else None
        research_artifacts = await repo.list_research_artifacts(factory_run_id)
        handoff_payload = self._build_research_handoff_payload(
            run=run,
            intent=intent,
            research_artifacts=research_artifacts,
        )

        packet = ReviewPacket(
            run_id=factory_run_id,
            promise=(intent.summary if intent else run.config.get("goal", run.config.get("opencode_worker", {}).get("goal", ""))),
            packet_type="research_handoff",
            status=run.status,
            wait_window_state="awaiting_review",
            branch_name=run.config.get("branch_name"),
            worker_id=None,
            worker_display_name=None,
            worker_machine_name=None,
            autonomy_level=run.config.get("autonomy_level"),
            template_id=run.template_id,
            template_version=run.config.get("template_version"),
            blast_radius={},
            safety_net_results={},
            execution_trace={},
            changed_files=[],
            diff_summary_uri=None,
            evaluator_verdict={},
            decision_gates={
                "packet_type": "research_handoff",
                "intent_id": intent.id if intent else None,
                "project_blueprint": run.config.get("project_blueprint"),
                "policy_result": run.config.get("policy_result"),
            },
            allowed_actions=self._compute_allowed_actions("awaiting_review"),
            research_artifact_ids=[artifact.id for artifact in research_artifacts],
            research_handoff=handoff_payload,
            telemetry_events=[
                {"event_type": "review_packet_created", "timestamp": utcnow().isoformat()},
            ],
        )
        await repo.save_review_packet(packet)
        await self._emit_worker_event(
            repo,
            worker_id="system",
            event_type="review_packet_created",
            payload={
                "review_packet_id": packet.id,
                "factory_run_id": factory_run_id,
                "packet_type": packet.packet_type,
                "research_artifact_ids": list(packet.research_artifact_ids),
            },
            factory_run_id=factory_run_id,
            review_packet_id=packet.id,
            correlation_id=run.correlation_id or packet.id,
            actor="system",
            idempotency_key=f"review-packet-created:{packet.id}",
        )
        return to_jsonable(packet)

    async def get_review_packet(self, factory_run_id: str) -> dict[str, Any]:
        repo = get_repository()
        packet = await repo.get_review_packet(factory_run_id)
        if not packet:
            raise ValueError("Review packet not found")
        result = to_jsonable(packet)
        run = await repo.get_factory_run(factory_run_id)
        if run:
            result["run_status"] = run.status
        return result

    async def list_review_packets(
        self,
        *,
        filter_group: str | None = None,
    ) -> dict[str, Any]:
        repo = get_repository()
        states: set[str] | None = None
        statuses: set[str] | None = None

        if filter_group == "active":
            states = {"awaiting_review", "wait_window", "paused"}
        elif filter_group == "awaiting_review":
            states = {"awaiting_review", "wait_window"}
        elif filter_group == "no_objection":
            states = {"no_objection_recorded", "ready_to_continue"}
        elif filter_group == "complete":
            states = {"approved", "rejected"}

        packets = await repo.list_review_packets(wait_window_states=states, statuses=statuses)

        enriched = []
        for packet in packets:
            entry = to_jsonable(packet)
            run = await repo.get_factory_run(packet.run_id)
            entry["run_status"] = run.status if run else "unknown"
            enriched.append(entry)

        return {"review_packets": enriched}

    async def submit_intervention(
        self,
        factory_run_id: str,
        action: str,
        *,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        repo = get_repository()
        packet = await repo.get_review_packet(factory_run_id)
        if not packet:
            raise ValueError("Review packet not found")

        new_state = self._action_to_state(action)
        if not self._is_valid_transition(packet.wait_window_state, new_state):
            raise InvalidTransitionError(
                f"Cannot transition from '{packet.wait_window_state}' to '{new_state}'"
            )

        if action in ("reject", "request_changes") and not rationale:
            raise ValueError(f"Rationale is required for '{action}' action")

        old_state = packet.wait_window_state
        created_work_item_id = None
        run = await repo.get_factory_run(factory_run_id)
        if packet.packet_type == "research_handoff" and new_state == "approved":
            created_work_item = await self._create_research_handoff_work_item(
                repo=repo,
                packet=packet,
                run=run,
                rationale=rationale,
            )
            created_work_item_id = created_work_item.id if created_work_item else None
        packet.wait_window_state = new_state
        packet.updated_at = utcnow()
        packet.resolved_at = utcnow() if new_state in ("approved", "rejected") else None

        if new_state == "approved":
            packet.status = "approved"

        event_type = self._packet_event_type(packet, action)
        event = {
            "event_type": event_type,
            "action": action,
            "from_state": old_state,
            "to_state": new_state,
            "rationale": rationale,
            "created_work_item_id": created_work_item_id,
            "timestamp": utcnow().isoformat(),
        }
        packet.telemetry_events = list(packet.telemetry_events) + [event]
        packet.allowed_actions = self._compute_allowed_actions(new_state)

        await repo.save_review_packet(packet)

        if run and new_state == "approved":
            run.status = "approved"
            await repo.save_factory_run(run)

        await self._emit_worker_event(
            repo,
            worker_id="system",
            event_type=event_type,
            payload=event,
            factory_run_id=factory_run_id,
            review_packet_id=packet.id,
            correlation_id=run.correlation_id if run else packet.id,
            actor="system",
            idempotency_key=f"{event_type}:{packet.id}:{new_state}",
        )

        return to_jsonable(packet)

    async def _create_research_handoff_work_item(
        self,
        *,
        repo: Any,
        packet: ReviewPacket,
        run: FactoryRun | None,
        rationale: str | None,
    ):
        if not run:
            raise ValueError("Factory run not found")

        project = await repo.get_project_twin(run.idea_id)
        template = await repo.get_template_pack(run.template_id)
        if not project or not template:
            raise ValueError("Project twin or template pack not found")

        blueprint = ProjectBlueprint.from_dict(dict(run.config.get("project_blueprint") or {}))
        policy_result = self._policy_engine.validate_blueprint(blueprint, project=project, template=template)
        if policy_result.status == "block":
            raise PolicyBlockedError(policy_result)

        research_handoff = dict(packet.research_handoff or {})
        work_payload = {
            "factory_run_id": run.id,
            "review_packet_id": packet.id,
            "packet_type": packet.packet_type,
            "work_type": "implementation",
            "goal": packet.promise or run.config.get("goal", ""),
            "research_artifact_ids": list(packet.research_artifact_ids),
            "research_handoff": research_handoff,
            "implementation_requirements": list(research_handoff.get("implementation_requirements") or []),
            "supported_facts": list(research_handoff.get("supported_facts") or []),
            "open_questions": list(research_handoff.get("open_questions") or []),
            "project_blueprint": blueprint.to_dict(),
            "policy_result": policy_result.to_dict(),
        }
        if packet.research_artifact_ids:
            work_payload["research_artifact_id"] = packet.research_artifact_ids[0]

        return await self._project_service.enqueue_job(
            idea_id=run.idea_id,
            project_id=project.id,
            job_type=FACTORY_WORKER_JOB_TYPE,
            payload=work_payload,
            idempotency_key=f"research-handoff:{packet.id}",
            priority=60,
            factory_run_id=run.id,
            rationale=rationale or packet.promise or None,
            correlation_id=run.correlation_id or packet.id,
            dedupe_hash=self._stable_hash({
                "factory_run_id": run.id,
                "review_packet_id": packet.id,
                "packet_type": packet.packet_type,
                "research_artifact_ids": packet.research_artifact_ids,
                "blueprint_id": blueprint.blueprint_id,
            }),
            budget=run.budget,
            stop_conditions=run.stop_conditions,
            branch_name=packet.branch_name or f"factory/{run.id[:8]}/research-handoff",
        )

    def _build_research_handoff_payload(
        self,
        *,
        run: FactoryRun,
        intent: Intent | None,
        research_artifacts: list[ResearchArtifact],
    ) -> dict[str, Any]:
        project_blueprint = dict(run.config.get("project_blueprint") or {})
        supported_facts: list[dict[str, Any]] = []
        interpretations: list[dict[str, Any]] = []
        implementation_requirements: list[dict[str, Any]] = []
        assumptions: list[dict[str, Any]] = []
        open_questions: list[dict[str, Any]] = []
        proposed_next_actions: list[dict[str, Any]] = []
        requirement_tags: list[dict[str, Any]] = []

        for artifact in research_artifacts:
            normalized = dict(artifact.normalized or {})
            summary = str(normalized.get("summary") or artifact.title or artifact.source).strip()
            key_points = list(normalized.get("key_points") or [])
            supported_facts.append({
                "text": summary,
                "artifact_id": artifact.id,
                "source": artifact.source,
                "evidence_status": "supported",
            })
            for idx, point in enumerate(key_points[:5]):
                interpretations.append({
                    "text": point,
                    "artifact_id": artifact.id,
                    "source": artifact.source,
                    "evidence_status": "inferred" if idx else "supported",
                })
                requirement_tags.append({
                    "label": point,
                    "evidence_status": "inferred" if idx else "supported",
                    "artifact_id": artifact.id,
                    "source": artifact.source,
                })
            if not key_points and summary:
                requirement_tags.append({
                    "label": summary,
                    "evidence_status": "supported",
                    "artifact_id": artifact.id,
                    "source": artifact.source,
                })

        build_steps = list(project_blueprint.get("build_steps") or [])
        verification_commands = list(project_blueprint.get("verification_commands") or [])
        for step in build_steps:
            implementation_requirements.append({
                "text": str(step),
                "evidence_status": "inferred",
                "source": "project_blueprint",
            })
            requirement_tags.append({
                "label": str(step),
                "evidence_status": "inferred",
                "source": "project_blueprint",
            })
        for command in verification_commands:
            requirement_tags.append({
                "label": str(command),
                "evidence_status": "supported",
                "source": "project_blueprint",
            })

        if intent:
            proposed_next_actions.append({
                "text": f"Implement the intent: {intent.summary}",
                "evidence_status": "supported",
                "source": "intent",
            })
        proposed_next_actions.extend([
            {"text": "Create the implementation work item after approval.", "evidence_status": "inferred", "source": "review_flow"},
            {"text": "Run the configured verification commands before closure.", "evidence_status": "supported", "source": "project_blueprint"},
        ])

        if not supported_facts:
            open_questions.append({
                "text": "No research artifacts are attached yet; confirm the evidence base before implementation.",
                "evidence_status": "open_question",
                "source": "system",
            })
            assumptions.append({
                "text": "Proceeding with the best available project blueprint and intent context.",
                "evidence_status": "assumption",
                "source": "system",
            })

        if intent and intent.stop_conditions:
            assumptions.append({
                "text": f"Honor stop conditions: {', '.join(intent.stop_conditions)}",
                "evidence_status": "assumption",
                "source": "intent",
            })

        return {
            "supported_facts": supported_facts,
            "interpretations": interpretations,
            "implementation_requirements": implementation_requirements,
            "assumptions": assumptions,
            "open_questions": open_questions,
            "proposed_next_actions": proposed_next_actions,
            "requirement_tags": requirement_tags,
        }

    async def _emit_worker_event(
        self,
        repo: Any,
        *,
        worker_id: str,
        event_type: str,
        payload: dict[str, Any],
        factory_run_id: str | None = None,
        review_packet_id: str | None = None,
        correlation_id: str | None = None,
        actor: str | None = None,
        idempotency_key: str | None = None,
    ) -> WorkerEvent:
        event = WorkerEvent(
            worker_id=worker_id,
            event_type=event_type,
            payload=payload,
            factory_run_id=factory_run_id,
            review_packet_id=review_packet_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            actor=actor,
        )
        await repo.add_worker_event(event)
        return event

    def _packet_event_type(self, packet: ReviewPacket, action: str) -> str:
        if packet.packet_type == "research_handoff":
            return {
                "approve": "research_handoff_approved",
                "reject": "research_handoff_rejected",
                "request_changes": "research_more_requested",
                "modify": "research_more_requested",
            }.get(action, "research_handoff_intervention")
        return "wait_window_intervention"

    def _stable_hash(self, payload: dict[str, Any]) -> str:
        import hashlib
        import json

        normalized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def record_expiry_transition(self, factory_run_id: str) -> dict[str, Any]:
        repo = get_repository()
        packet = await repo.get_review_packet(factory_run_id)
        if not packet:
            raise ValueError("Review packet not found")

        if packet.wait_window_state not in ("wait_window", "awaiting_review"):
            raise InvalidTransitionError(
                f"Cannot expire from state '{packet.wait_window_state}'"
            )

        old_state = packet.wait_window_state
        packet.wait_window_state = "no_objection_recorded"
        packet.updated_at = utcnow()

        event = {
            "event_type": "wait_window_expired_no_objection",
            "from_state": old_state,
            "to_state": "no_objection_recorded",
            "timestamp": utcnow().isoformat(),
        }
        packet.telemetry_events = list(packet.telemetry_events) + [event]
        packet.allowed_actions = self._compute_allowed_actions("no_objection_recorded")

        await repo.save_review_packet(packet)
        return to_jsonable(packet)

    async def start_wait_window(self, factory_run_id: str, expires_at: str | None = None) -> dict[str, Any]:
        repo = get_repository()
        packet = await repo.get_review_packet(factory_run_id)
        if not packet:
            raise ValueError("Review packet not found")

        if not self._is_valid_transition(packet.wait_window_state, "wait_window"):
            raise InvalidTransitionError(
                f"Cannot start wait window from '{packet.wait_window_state}'"
            )

        old_state = packet.wait_window_state
        packet.wait_window_state = "wait_window"
        packet.wait_window_started_at = utcnow()
        if expires_at:
            from backend.app.repository import _dt
            packet.expires_at = _dt(expires_at)
        else:
            from datetime import timedelta
            packet.expires_at = utcnow() + timedelta(minutes=15)
        packet.updated_at = utcnow()

        event = {
            "event_type": "wait_window_started",
            "from_state": old_state,
            "to_state": "wait_window",
            "expires_at": packet.expires_at.isoformat() if packet.expires_at else None,
            "timestamp": utcnow().isoformat(),
        }
        packet.telemetry_events = list(packet.telemetry_events) + [event]
        packet.allowed_actions = self._compute_allowed_actions("wait_window")

        await repo.save_review_packet(packet)
        return to_jsonable(packet)

    def _is_valid_transition(self, from_state: str, to_state: str) -> bool:
        allowed = VALID_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    def _action_to_state(self, action: str) -> str:
        mapping = {
            "approve": "approved",
            "reject": "rejected",
            "request_changes": "modification_requested",
            "modify": "modification_requested",
            "pause": "paused",
            "continue_after_no_objection": "ready_to_continue",
        }
        if action not in mapping:
            raise ValueError(f"Unknown action: {action}. Valid: {', '.join(sorted(mapping))}")
        return mapping[action]

    def _compute_allowed_actions(self, state: str) -> list[str]:
        if state == "approved":
            return []
        if state == "rejected":
            return []
        base = ["approve", "reject", "pause"]
        if state in ("no_objection_recorded", "ready_to_continue"):
            base.append("continue_after_no_objection")
        if state in ("awaiting_review", "wait_window"):
            base.append("request_changes")
        return base

    def _compute_blast_radius(
        self,
        verifications: list[VerificationRun],
        repair_tasks: list[RepairTask],
        work_items: list,
    ) -> dict[str, Any]:
        all_changed: list[str] = []
        for v in verifications:
            all_changed.extend(v.changed_files or [])
        for t in repair_tasks:
            all_changed.extend(t.changed_files or [])
        unique_files = list(dict.fromkeys(all_changed))

        impact_score = "low"
        if len(unique_files) > 10:
            impact_score = "high"
        elif len(unique_files) > 3:
            impact_score = "medium"

        return {
            "impact_score": impact_score,
            "impacted_files": unique_files[:50],
            "impacted_modules": list(dict.fromkeys(
                "/".join(f.split("/")[:2]) for f in unique_files if "/" in f
            )),
            "total_files_changed": len(unique_files),
        }

    def _compute_safety_net(
        self,
        verifications: list[VerificationRun],
        repair_tasks: list[RepairTask],
        manifest: Any,
        *,
        template_id: str,
        template_version: str | None,
        verification_expectations: list[str],
        graphify_expectations: dict[str, Any],
        path_guardrails: dict[str, Any],
        guardrail_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tests_passed = all(
            v.status in ("passed", "completed", "succeeded", "success")
            for v in verifications
        ) if verifications else True

        graphify_status = "pending"
        if manifest and hasattr(manifest, "graphify_status"):
            graphify_status = manifest.graphify_status

        failed_verifications = [v for v in verifications if v.status == "failed"]
        error_count = len(failed_verifications)

        verification_commands: list[str] = []
        if verifications:
            for v in verifications:
                if v.verification_type:
                    verification_commands.append(v.verification_type)

        guardrail_pass = True
        if guardrail_result:
            guardrail_pass = bool(guardrail_result.get("valid", True))

        return {
            "template_id": template_id,
            "template_version": template_version,
            "tests_passed": tests_passed,
            "graphify_status": graphify_status,
            "verification_commands": list(dict.fromkeys(verification_commands)),
            "verification_expectations": list(verification_expectations),
            "graphify_expectations": graphify_expectations,
            "path_guardrails": path_guardrails,
            "error_count": error_count,
            "lint_errors": sum(1 for v in failed_verifications if v.failure_classification == "lint"),
            "repair_loop_triggered": len(repair_tasks) > 0,
            "repair_count": len(repair_tasks),
            "guardrail_pass": guardrail_pass,
            "guardrail_result": guardrail_result or {},
        }

    def _compute_execution_trace(
        self,
        batches: list,
        verifications: list[VerificationRun],
        repair_tasks: list[RepairTask],
        work_items: list,
    ) -> dict[str, Any]:
        entries = []
        for item in work_items:
            payload = item.payload or {}
            entries.append({
                "type": "work_item",
                "job_type": item.job_type,
                "status": item.status,
                "branch": payload.get("branch"),
                "outcome": "completed" if item.status == "completed" else item.status,
            })
        for v in verifications:
            entries.append({
                "type": "verification",
                "verification_type": v.verification_type,
                "status": v.status,
                "failure_classification": v.failure_classification or None,
                "outcome": v.status,
            })
        for t in repair_tasks:
            entries.append({
                "type": "repair",
                "attempt": t.attempt_number,
                "status": t.status,
                "classification": t.failure_classification,
                "outcome": t.status,
            })

        return {
            "entries": entries,
            "total_steps": len(entries),
            "repair_loop_triggered": any(e["type"] == "repair" for e in entries),
        }

    def _collect_changed_files(
        self,
        verifications: list[VerificationRun],
        repair_tasks: list[RepairTask],
    ) -> list[str]:
        all_files: list[str] = []
        for v in verifications:
            all_files.extend(v.changed_files or [])
        for t in repair_tasks:
            all_files.extend(t.changed_files or [])
        return list(dict.fromkeys(all_files))

    def _compute_diff_uri(self, run: FactoryRun, changed_files: list[str]) -> str | None:
        if not changed_files:
            return None
        return f"s3://factory-artifacts/{run.id}/diff-summary.json"

    def _compute_evaluator_verdict(
        self,
        verifications: list[VerificationRun],
        safety_net: dict[str, Any],
    ) -> dict[str, Any]:
        tests_passed = safety_net.get("tests_passed", True)
        repair_triggered = safety_net.get("repair_loop_triggered", False)

        verdict = "pass"
        if not tests_passed:
            verdict = "fail"
        elif repair_triggered:
            verdict = "conditional_pass"

        return {
            "verdict": verdict,
            "justification": (
                "DETERMINISTIC PLACEHOLDER: No secondary evaluator configured. "
                "Verdict based on verification pass/fail status. "
                "Deploy a secondary evaluator service for production-grade assessment."
            ),
            "confidence_score": 1.0 if tests_passed and not repair_triggered else 0.6,
            "source": "deterministic_placeholder",
        }
