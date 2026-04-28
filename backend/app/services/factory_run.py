from __future__ import annotations

from typing import Any

from backend.app.repository import (
    AUTONOMY_AUTONOMOUS_DEVELOPMENT,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    ProjectTwin,
    TemplateArtifact,
    TemplatePack,
    WorkItem,
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

    async def create_factory_run(
        self,
        project_id: str,
        template_id: str,
        autonomy_level: str = AUTONOMY_AUTONOMOUS_DEVELOPMENT,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repo = get_repository()
        project = await repo.get_project_twin_by_id(project_id)
        if not project:
            raise ValueError("Project twin not found")

        template = await repo.get_template_pack(template_id)
        if not template:
            raise ValueError("Template pack not found")

        config = dict(config or {})
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
        )
        policy_result = self._policy_engine.validate_blueprint(
            blueprint,
            project=project,
            template=template,
        )
        if policy_result.status == "block":
            raise PolicyBlockedError(policy_result)

        run_config = {
            **config,
            "autonomy_level": autonomy_level,
            "template_version": template.version,
            "template_id": template.template_id,
            "project_blueprint": to_jsonable(blueprint),
            "policy_result": policy_result.to_dict(),
        }
        if policy_result.feedback:
            run_config["planner_feedback"] = list(policy_result.feedback)

        factory_run = FactoryRun(
            idea_id=project.idea_id,
            template_id=template.template_id,
            status="queued",
            config=dict(run_config),
        )
        role_contracts = await self._build_role_contracts(
            project=project,
            template=template,
            factory_run_id=factory_run.id,
            run_config=run_config,
        )
        factory_run.config["role_contracts"] = role_contracts
        await repo.create_factory_run(factory_run)

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
            )

            if can_enqueue_work(factory_run):
                work_item = await self._project_service.enqueue_job(
                    idea_id=project.idea_id,
                    project_id=project.id,
                    job_type=FACTORY_WORKER_JOB_TYPE,
                    payload=worker_contract,
                    idempotency_key=f"factory:{factory_run.id}:phase:{first_phase.phase_key}",
                    priority=60,
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
        return {
            "factory_run": to_jsonable(bundle["factory_run"]),
            "phases": [to_jsonable(p) for p in bundle["phases"]],
            "first_batch": to_jsonable(first_batch) if first_batch else None,
            "work_item": to_jsonable(work_item) if work_item else None,
            "tracking_manifest": to_jsonable(bundle["tracking_manifest"]),
            "tracking_summary": bundle["tracking_summary"],
        }

    async def get_factory_run(self, factory_run_id: str) -> dict[str, Any]:
        repo = get_repository()
        bundle = await collect_factory_run_bundle(repo, factory_run_id)
        if not bundle:
            raise ValueError("Factory run not found")
        return {
            "factory_run": to_jsonable(bundle["factory_run"]),
            "phases": [to_jsonable(p) for p in bundle["phases"]],
            "batches": [to_jsonable(b) for b in bundle["batches"]],
            "verifications": [to_jsonable(v) for v in bundle["verifications"]],
            "tracking_manifest": to_jsonable(bundle["tracking_manifest"]),
            "tracking_summary": bundle["tracking_summary"],
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

    async def _build_worker_contract(
        self,
        project: ProjectTwin,
        template: TemplatePack,
        factory_run: FactoryRun,
        phase: FactoryPhase,
        batch: FactoryBatch,
    ) -> dict[str, Any]:
        repo = get_repository()
        template_docs = await self._collect_template_docs(repo, template.template_id)
        code_index = await repo.get_latest_code_index(project.idea_id)
        project_blueprint = dict((factory_run.config or {}).get("project_blueprint") or {})
        permission_profile = project_blueprint.get("permission_profile") or {}
        policy_result = (factory_run.config or {}).get("policy_result") or {}

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
            "goal": opencode_worker.get("goal") or f"Execute factory phase '{phase.phase_key}' for project {project.repo_full_name}",
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
            "response_schema": role_prompt["output_schema"],
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
    ) -> dict[str, Any]:
        repo = get_repository()
        template_docs = await self._collect_template_docs(repo, template.template_id)
        code_index = await repo.get_latest_code_index(project.idea_id)
        code_context = {
            "template_docs": template_docs,
            "code_index": to_jsonable(code_index) if code_index else {},
            "constraints": template.constraints or [],
            "quality_gates": template.quality_gates or [],
        }
        research_context = {
            "project_description": project.desired_outcome or project.current_status or "",
            "detected_stack": project.detected_stack,
            "test_commands": project.test_commands,
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
    ) -> ProjectBlueprint:
        repo = get_repository()
        code_index = await repo.get_latest_code_index(project.idea_id)
        blueprint_raw = config.get("blueprint")
        blueprint_config = blueprint_raw if isinstance(blueprint_raw, dict) else {}

        build_steps = blueprint_config["build_steps"] if "build_steps" in blueprint_config else self._derive_build_steps(template)
        verification_commands = (
            blueprint_config["verification_commands"]
            if "verification_commands" in blueprint_config
            else self._derive_verification_commands(project=project, template=template)
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
            "graphify_requirements": blueprint_config["graphify_requirements"] if "graphify_requirements" in blueprint_config else self._default_graphify_requirements(),
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

    def _derive_verification_commands(self, *, project: ProjectTwin, template: TemplatePack) -> list[str]:
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

    def _default_graphify_requirements(self) -> dict[str, list[str]]:
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
