from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from backend.app.repository import (
    TemplateArtifact,
    TemplateManifest,
    TemplatePack,
    get_repository,
    utcnow,
)
from backend.app.services.project_twin import to_jsonable


BUILTIN_TEMPLATE_ID = "karkhana-golden-sveltekit-supabase-stripe"
BUILTIN_TEMPLATE_VERSION = "0.0.1"
BUILTIN_SCHEMA_VERSION = "v0"

ROOT_AGENTS_KEY = "AGENTS.md"
OVERRIDE_AGENTS_KEY = "AGENTS.override.md"
SPEC_KEY = ".spec.md"
MEMORY_KEY = ".memory.md"


@dataclass(slots=True)
class TemplatePackManifestArtifactRef:
    key: str
    path: str
    kind: str
    description: str = ""
    required: bool = True
    scope_path: str | None = None
    storage_key: str | None = None


@dataclass(slots=True)
class TemplatePackManifestV0:
    id: str
    name: str
    version: str
    schema_version: str
    description: str
    stack: dict[str, Any] = field(default_factory=dict)
    required_tools: list[str] = field(default_factory=list)
    artifacts: list[TemplatePackManifestArtifactRef] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    graphify_expectations: dict[str, Any] = field(default_factory=dict)
    guardrails: list[str] = field(default_factory=list)
    review_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = [asdict(artifact) for artifact in self.artifacts]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplatePackManifestV0":
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            version=str(data.get("version") or ""),
            schema_version=str(data.get("schema_version") or BUILTIN_SCHEMA_VERSION),
            description=str(data.get("description") or ""),
            stack=dict(data.get("stack") or {}),
            required_tools=[str(item) for item in data.get("required_tools") or [] if str(item).strip()],
            artifacts=[
                TemplatePackManifestArtifactRef(
                    key=str(item.get("key") or ""),
                    path=str(item.get("path") or ""),
                    kind=str(item.get("kind") or "artifact"),
                    description=str(item.get("description") or ""),
                    required=bool(item.get("required", True)),
                    scope_path=item.get("scope_path"),
                    storage_key=item.get("storage_key"),
                )
                for item in data.get("artifacts") or []
            ],
            allowed_paths=[str(item) for item in data.get("allowed_paths") or [] if str(item).strip()],
            forbidden_paths=[str(item) for item in data.get("forbidden_paths") or [] if str(item).strip()],
            verification_commands=[str(item) for item in data.get("verification_commands") or [] if str(item).strip()],
            graphify_expectations=dict(data.get("graphify_expectations") or {}),
            guardrails=[str(item) for item in data.get("guardrails") or [] if str(item).strip()],
            review_metadata=dict(data.get("review_metadata") or {}),
        )


@dataclass(slots=True)
class TemplatePackValidationIssue:
    code: str
    message: str
    severity: str = "warn"
    field_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TemplatePackValidationResult:
    template_id: str
    version: str
    valid: bool
    issues: list[TemplatePackValidationIssue] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    guardrail_state: str = "pass"
    graphify_state: str = "pending"
    verification_state: str = "pending"
    checked_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["issues"] = [asdict(issue) for issue in self.issues]
        return payload


class TemplatePackService:
    def __init__(self, repo: Any | None = None) -> None:
        self._repo = repo or get_repository()

    async def ensure_seeded(self) -> None:
        await self._seed_builtin_pack()

    async def list_template_packs(self) -> list[dict[str, Any]]:
        await self.ensure_seeded()
        packs = await self._repo.list_template_packs()
        responses: list[dict[str, Any]] = []
        for pack in packs:
            manifest = await self._fetch_manifest(pack)
            responses.append(self._pack_response(pack, manifest))
        return responses

    async def get_template_pack(self, template_id: str) -> dict[str, Any] | None:
        await self.ensure_seeded()
        pack = await self._repo.get_template_pack(template_id)
        if not pack:
            return None
        manifest = await self._fetch_manifest(pack)
        return self._pack_response(pack, manifest)

    async def get_template_manifest(self, template_id: str) -> dict[str, Any] | None:
        await self.ensure_seeded()
        pack = await self._repo.get_template_pack(template_id)
        if not pack:
            return None
        manifest = await self._fetch_manifest(pack)
        return manifest.to_dict()

    async def build_registry_context(self, template_id: str, *, target_path: str | None = None) -> dict[str, Any] | None:
        manifest = await self.get_template_manifest(template_id)
        if not manifest:
            return None
        return {
            "template_manifest": manifest,
            "verification_commands": list(manifest.get("verification_commands") or []),
            "graphify_expectations": dict(manifest.get("graphify_expectations") or {}),
            "path_guardrails": {
                "allowed_paths": list(manifest.get("allowed_paths") or []),
                "forbidden_paths": list(manifest.get("forbidden_paths") or []),
            },
            "resolved_agents": await self.resolve_agents_hierarchy(template_id, target_path=target_path or "."),
            "review_metadata": dict(manifest.get("review_metadata") or {}),
        }

    async def validate_template(
        self,
        template_id: str,
        *,
        changed_files: list[str] | None = None,
        mode: str = "normal",
        verification_commands: list[str] | None = None,
        graphify_updated: bool | None = None,
        completed: bool = False,
    ) -> dict[str, Any]:
        manifest = await self.get_template_manifest(template_id)
        if not manifest:
            raise ValueError("Template pack not found")

        result = await self._validate_manifest(template_id, manifest)
        checked_paths = [self._normalize_path(path) for path in (changed_files or []) if str(path).strip()]
        result.checked_paths = checked_paths
        if checked_paths:
            result.issues.extend(self._validate_paths(manifest, checked_paths, mode=mode))

        commands = [str(command).strip() for command in (verification_commands or manifest.get("verification_commands") or []) if str(command).strip()]
        if completed and not commands:
            result.issues.append(TemplatePackValidationIssue(
                code="missing_verification_commands",
                field_name="verification_commands",
                severity="block",
                message="Completion requires verification commands.",
            ))
        if manifest.get("verification_commands") and "pnpm run check" not in commands:
            result.issues.append(TemplatePackValidationIssue(
                code="verification_command_gap",
                field_name="verification_commands",
                severity="warn",
                message="Verification commands do not include the canonical checks.",
                details={"expected": manifest.get("verification_commands")},
            ))

        graphify_expectations = dict(manifest.get("graphify_expectations") or {})
        if graphify_expectations:
            if graphify_updated is False:
                result.issues.append(TemplatePackValidationIssue(
                    code="graphify_not_updated",
                    field_name="graphify_expectations",
                    severity="block",
                    message="Graphify update was required but not completed.",
                    details={"expected": graphify_expectations},
                ))
            if not any("graphify update ." in command for command in commands):
                result.issues.append(TemplatePackValidationIssue(
                    code="missing_graphify_command",
                    field_name="verification_commands",
                    severity="block",
                    message="Graphify expectations are configured but the update command is missing.",
                    details={"expected": graphify_expectations},
                ))

        result.verification_state = "pass" if not any(issue.field_name == "verification_commands" and issue.severity == "block" for issue in result.issues) else "fail"
        result.graphify_state = "pass" if not any(issue.field_name == "graphify_expectations" and issue.severity == "block" for issue in result.issues) else "fail"
        result.guardrail_state = "pass" if not any(issue.field_name == "path_guardrails" and issue.severity == "block" for issue in result.issues) else "fail"
        result.valid = not any(issue.severity == "block" for issue in result.issues)
        return result.to_dict()

    async def validate_factory_run_guardrails(
        self,
        template_id: str,
        *,
        changed_files: list[str] | None = None,
        verification_commands: list[str] | None = None,
        graphify_updated: bool | None = None,
        mode: str = "normal",
        completed: bool = False,
    ) -> dict[str, Any]:
        return await self.validate_template(
            template_id,
            changed_files=changed_files,
            verification_commands=verification_commands,
            graphify_updated=graphify_updated,
            mode=mode,
            completed=completed,
        )

    async def resolve_agents_hierarchy(self, template_id: str, *, target_path: str = ".") -> list[dict[str, Any]]:
        await self.ensure_seeded()
        manifest = await self.get_template_manifest(template_id)
        if not manifest:
            return []

        normalized_target = self._normalize_path(target_path)
        artifacts = [item for item in manifest.get("artifacts") or [] if item.get("key") in {ROOT_AGENTS_KEY, OVERRIDE_AGENTS_KEY}]
        resolved: list[dict[str, Any]] = []

        root_ref = next((item for item in artifacts if item.get("key") == ROOT_AGENTS_KEY), None)
        if root_ref:
            resolved.append(await self._resolve_artifact(template_id, root_ref))

        overrides = [
            item for item in artifacts
            if item.get("key") == OVERRIDE_AGENTS_KEY
            and self._path_matches_scope(normalized_target, str(item.get("scope_path") or item.get("path") or ""))
        ]
        overrides.sort(key=lambda item: (self._scope_depth(str(item.get("scope_path") or item.get("path") or "")), str(item.get("scope_path") or item.get("path") or "")))
        for item in overrides:
            resolved.append(await self._resolve_artifact(template_id, item))
        return [item for item in resolved if item]

    async def _seed_builtin_pack(self) -> None:
        existing = await self._repo.get_template_pack(BUILTIN_TEMPLATE_ID)
        if existing:
            return

        manifest = self._builtin_manifest()
        pack = TemplatePack(
            template_id=manifest.id,
            version=manifest.version,
            channel="stable",
            display_name=manifest.name,
            description=manifest.description,
            phases=[
                {"key": "scaffold", "label": "Scaffold"},
                {"key": "verification", "label": "Verification"},
                {"key": "fixtures", "label": "Fixtures"},
            ],
            quality_gates=[
                {"phase": "verification", "type": "graphify", "command": "graphify update ."},
            ],
            default_stack={
                "stack": manifest.stack.get("name", []),
                "package_manager": manifest.stack.get("package_manager", "pnpm"),
                "framework": manifest.stack.get("framework", []),
            },
            constraints=[
                {"id": "path-guardrails", "description": "Only allowed paths may change during normal runs."},
                {"id": "no-transcripts", "description": "Memory artifacts must stay compact and decision oriented."},
            ],
            opencode_worker={
                "goal": "Maintain the golden SaaS registry for Karkhana",
                "verification_commands": list(manifest.verification_commands),
                "deliverables": [
                    "Normalized template manifest",
                    "AGENTS hierarchy resolution",
                    "Path guardrail validation",
                    "Verification and Graphify expectations",
                ],
            },
        )
        await self._repo.save_template_pack(pack)
        await self._repo.save_template_manifest(TemplateManifest(
            template_id=manifest.id,
            version=manifest.version,
            artifact_keys=[item.storage_key or item.key for item in manifest.artifacts],
            metadata_=manifest.to_dict(),
        ))

        await self._seed_builtin_artifacts(manifest)

    async def _seed_builtin_artifacts(self, manifest: TemplatePackManifestV0) -> None:
        artifacts = [
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key=ROOT_AGENTS_KEY,
                content_type="text/markdown",
                uri=f"template://{manifest.id}/{ROOT_AGENTS_KEY}",
                content=self._root_agents_content(manifest),
                version=manifest.version,
                metadata_={"kind": "agents", "scope_path": "."},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key="AGENTS.override.md#backend",
                content_type="text/markdown",
                uri=f"template://{manifest.id}/AGENTS.override.md?scope=backend",
                content=self._override_content("backend", "FastAPI boundaries, API contracts, and backend data integrity come first."),
                version=manifest.version,
                metadata_={"kind": "agents_override", "scope_path": "backend", "canonical_key": OVERRIDE_AGENTS_KEY},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key="AGENTS.override.md#frontend",
                content_type="text/markdown",
                uri=f"template://{manifest.id}/AGENTS.override.md?scope=frontend",
                content=self._override_content("frontend", "SvelteKit components should stay small, typed, and visually intentional."),
                version=manifest.version,
                metadata_={"kind": "agents_override", "scope_path": "frontend", "canonical_key": OVERRIDE_AGENTS_KEY},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key=SPEC_KEY,
                content_type="text/markdown",
                uri=f"template://{manifest.id}/{SPEC_KEY}",
                content="# Template Pack Standard v0\n\n- Stack: SvelteKit + Supabase + Stripe\n- Package manager: pnpm\n- Verification: pnpm install, pnpm run check, pnpm test, supabase db reset, graphify update .\n",
                version=manifest.version,
                metadata_={"kind": "spec"},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key=MEMORY_KEY,
                content_type="text/markdown",
                uri=f"template://{manifest.id}/{MEMORY_KEY}",
                content=(
                    "# Execution Summary\n"
                    "- Added Template Pack Standard v0 registry metadata.\n\n"
                    "## Decision Log\n"
                    "- Keep TemplatePack as a summary record.\n"
                    "- Store the canonical manifest in TemplateManifest.metadata_.\n"
                ),
                version=manifest.version,
                metadata_={"kind": "memory"},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key="ProjectBlueprint",
                content_type="application/json",
                uri=f"template://{manifest.id}/ProjectBlueprint",
                content='{"template":"ProjectBlueprint","stack":"SvelteKit + Supabase + Stripe"}',
                version=manifest.version,
                metadata_={"kind": "contract"},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key="scaffold",
                content_type="text/plain",
                uri=f"template://{manifest.id}/scaffold",
                content="Scaffold the application shell, data model, and environment wiring.",
                version=manifest.version,
                metadata_={"kind": "phase"},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key="verification",
                content_type="text/plain",
                uri=f"template://{manifest.id}/verification",
                content="Verify the build, tests, Supabase reset, and Graphify refresh.",
                version=manifest.version,
                metadata_={"kind": "phase"},
            ),
            TemplateArtifact(
                template_id=manifest.id,
                artifact_key="fixtures",
                content_type="text/plain",
                uri=f"template://{manifest.id}/fixtures",
                content="Seed fixtures for the registry, validation, and read-only views.",
                version=manifest.version,
                metadata_={"kind": "phase"},
            ),
        ]
        for artifact in artifacts:
            existing = await self._repo.get_template_artifact(manifest.id, artifact.artifact_key)
            if not existing:
                await self._repo.save_template_artifact(artifact)

    def _builtin_manifest(self) -> TemplatePackManifestV0:
        return TemplatePackManifestV0(
            id=BUILTIN_TEMPLATE_ID,
            name="Karkhana Golden SaaS Registry",
            version=BUILTIN_TEMPLATE_VERSION,
            schema_version=BUILTIN_SCHEMA_VERSION,
            description="Golden registry pack for a SvelteKit + Supabase + Stripe SaaS baseline.",
            stack={
                "name": ["SvelteKit", "Supabase", "Stripe"],
                "package_manager": "pnpm",
                "framework": ["SvelteKit"],
                "backend": ["Supabase"],
            },
            required_tools=["node", "pnpm", "supabase", "stripe"],
            artifacts=[
                TemplatePackManifestArtifactRef(key=ROOT_AGENTS_KEY, path=".", kind="prompt", description="Root AGENTS prompt."),
                TemplatePackManifestArtifactRef(key=OVERRIDE_AGENTS_KEY, path="backend", kind="prompt_override", description="Backend scoped prompt override.", scope_path="backend", storage_key="AGENTS.override.md#backend"),
                TemplatePackManifestArtifactRef(key=OVERRIDE_AGENTS_KEY, path="frontend", kind="prompt_override", description="Frontend scoped prompt override.", scope_path="frontend", storage_key="AGENTS.override.md#frontend"),
                TemplatePackManifestArtifactRef(key=SPEC_KEY, path="docs", kind="spec", description="First-class spec artifact."),
                TemplatePackManifestArtifactRef(key=MEMORY_KEY, path="memory", kind="memory", description="First-class execution memory artifact."),
                TemplatePackManifestArtifactRef(key="ProjectBlueprint", path="backend/app/services/policy_engine.py", kind="contract", description="Project blueprint contract."),
                TemplatePackManifestArtifactRef(key="scaffold", path="backend/app/services/factory_run.py", kind="phase", description="Scaffold phase artifact."),
                TemplatePackManifestArtifactRef(key="verification", path="backend/app/services/factory_run.py", kind="phase", description="Verification phase artifact."),
                TemplatePackManifestArtifactRef(key="fixtures", path="backend/tests", kind="fixtures", description="Test fixture artifacts."),
            ],
            allowed_paths=[
                "backend/**",
                "frontend/**",
                "docs/**",
                "scripts/**",
                "tests/**",
                "graphify-out/**",
            ],
            forbidden_paths=[
                ".karkhana/**",
                "backend/tests/verification/**",
                "frontend/src/lib/components/verification/**",
            ],
            verification_commands=[
                "pnpm install",
                "pnpm run check",
                "pnpm test",
                "supabase db reset",
                "graphify update .",
            ],
            graphify_expectations={
                "read_before_task": [
                    "graphify-out/GRAPH_REPORT.md",
                    "graphify-out/wiki/index.md",
                ],
                "refresh_after_task": ["graphify update ."],
            },
            guardrails=[
                "Normal runs must stay within allowed_paths and never touch .karkhana/**.",
                "Verification harness edits are rejected during normal runs.",
                "Graphify is required whenever configured expectations are present.",
            ],
            review_metadata={
                "template_id": BUILTIN_TEMPLATE_ID,
                "template_version": BUILTIN_TEMPLATE_VERSION,
                "verification_expectations": [
                    "pnpm install",
                    "pnpm run check",
                    "pnpm test",
                    "supabase db reset",
                    "graphify update .",
                ],
                "graphify_status": "required",
                "guardrail_policy": "strict",
            },
        )

    def _pack_response(self, pack: TemplatePack, manifest: TemplatePackManifestV0 | None = None) -> dict[str, Any]:
        manifest_payload = manifest.to_dict() if manifest else None
        return {
            "id": pack.id,
            "template_id": pack.template_id,
            "version": pack.version,
            "channel": pack.channel,
            "display_name": pack.display_name,
            "description": pack.description,
            "default_stack": pack.default_stack,
            "phases": pack.phases,
            "quality_gates": pack.quality_gates,
            "constraints": pack.constraints,
            "opencode_worker": pack.opencode_worker,
            "required_tools": list(manifest_payload.get("required_tools") or []) if manifest_payload else [],
            "verification_commands": list(manifest_payload.get("verification_commands") or []) if manifest_payload else list((pack.opencode_worker or {}).get("verification_commands") or []),
            "graphify_expectations": dict(manifest_payload.get("graphify_expectations") or {}) if manifest_payload else {},
            "allowed_paths": list(manifest_payload.get("allowed_paths") or []) if manifest_payload else [],
            "forbidden_paths": list(manifest_payload.get("forbidden_paths") or []) if manifest_payload else [],
            "guardrails": list(manifest_payload.get("guardrails") or []) if manifest_payload else list(pack.constraints or []),
            "artifact_refs": list(manifest_payload.get("artifacts") or []) if manifest_payload else [],
            "review_metadata": dict(manifest_payload.get("review_metadata") or {}) if manifest_payload else {},
            "created_at": to_jsonable(pack.created_at),
            "updated_at": to_jsonable(pack.updated_at),
            "manifest": manifest_payload,
        }

    async def _fetch_manifest(self, pack: TemplatePack) -> TemplatePackManifestV0:
        manifest = await self._repo.get_template_manifest(pack.template_id, pack.version)
        if manifest and manifest.metadata_:
            return TemplatePackManifestV0.from_dict(manifest.metadata_)
        fallback = self._manifest_from_pack(pack)
        await self._repo.save_template_manifest(TemplateManifest(
            template_id=pack.template_id,
            version=pack.version,
            artifact_keys=[],
            metadata_=fallback.to_dict(),
        ))
        return fallback

    def _manifest_from_pack(self, pack: TemplatePack) -> TemplatePackManifestV0:
        default_stack = dict(pack.default_stack or {})
        stack = {
            "name": default_stack.get("stack") or default_stack.get("framework") or [],
            "package_manager": default_stack.get("package_manager", "pnpm"),
            "framework": default_stack.get("framework") or [],
        }
        opencode_worker = dict(pack.opencode_worker or {})
        verification_commands = [str(item) for item in opencode_worker.get("verification_commands") or [] if str(item).strip()]
        if "graphify update ." not in verification_commands:
            verification_commands.append("graphify update .")
        return TemplatePackManifestV0(
            id=pack.template_id,
            name=pack.display_name or pack.template_id,
            version=pack.version,
            schema_version=BUILTIN_SCHEMA_VERSION,
            description=pack.description or "",
            stack=stack,
            required_tools=["node", "pnpm"],
            artifacts=[
                TemplatePackManifestArtifactRef(key=ROOT_AGENTS_KEY, path=".", kind="prompt", description="Compatibility AGENTS prompt."),
                TemplatePackManifestArtifactRef(key=SPEC_KEY, path="docs", kind="spec", description="Compatibility spec artifact."),
                TemplatePackManifestArtifactRef(key=MEMORY_KEY, path="memory", kind="memory", description="Compatibility memory artifact."),
            ],
            allowed_paths=["backend/**", "frontend/**", "docs/**", "scripts/**", "tests/**"],
            forbidden_paths=[".karkhana/**"],
            verification_commands=verification_commands,
            graphify_expectations={
                "read_before_task": ["graphify-out/GRAPH_REPORT.md"],
                "refresh_after_task": ["graphify update ."],
            },
            guardrails=[
                "Keep compatibility runs read-only unless a manifest explicitly allows edits.",
                "Prefer narrow, repo-local changes when a template has no dedicated registry pack.",
            ] + [str(item) for item in (pack.constraints or []) if str(item).strip()],
            review_metadata={"template_id": pack.template_id, "template_version": pack.version},
        )

    async def _validate_manifest(self, template_id: str, manifest: dict[str, Any]) -> TemplatePackValidationResult:
        issues: list[TemplatePackValidationIssue] = []
        required_fields = [
            "id",
            "name",
            "version",
            "schema_version",
            "description",
            "stack",
            "required_tools",
            "artifacts",
            "allowed_paths",
            "forbidden_paths",
            "verification_commands",
            "graphify_expectations",
            "guardrails",
            "review_metadata",
        ]
        for field_name in required_fields:
            if field_name not in manifest or manifest[field_name] in (None, "", [], {}):
                issues.append(TemplatePackValidationIssue(
                    code=f"missing_{field_name}",
                    field_name=field_name,
                    severity="block",
                    message=f"Manifest field '{field_name}' is required.",
                ))

        if manifest.get("schema_version") != BUILTIN_SCHEMA_VERSION:
            issues.append(TemplatePackValidationIssue(
                code="schema_version",
                field_name="schema_version",
                severity="warn",
                message="Schema version is not normalized to v0.",
                details={"expected": BUILTIN_SCHEMA_VERSION},
            ))

        artifacts = list(manifest.get("artifacts") or [])
        if not artifacts:
            issues.append(TemplatePackValidationIssue(
                code="missing_artifacts",
                field_name="artifacts",
                severity="block",
                message="At least one artifact reference is required.",
            ))
        for artifact in artifacts:
            issues.extend(await self._validate_artifact_ref(template_id, artifact))

        if not manifest.get("verification_commands"):
            issues.append(TemplatePackValidationIssue(
                code="missing_verification_commands",
                field_name="verification_commands",
                severity="block",
                message="Verification commands are required.",
            ))

        if not manifest.get("allowed_paths"):
            issues.append(TemplatePackValidationIssue(
                code="missing_allowed_paths",
                field_name="allowed_paths",
                severity="block",
                message="Allowed paths are required.",
            ))

        if not manifest.get("forbidden_paths"):
            issues.append(TemplatePackValidationIssue(
                code="missing_forbidden_paths",
                field_name="forbidden_paths",
                severity="warn",
                message="Forbidden paths should be declared for guardrails.",
            ))

        return TemplatePackValidationResult(
            template_id=str(manifest.get("id") or ""),
            version=str(manifest.get("version") or ""),
            valid=not any(issue.severity == "block" for issue in issues),
            issues=issues,
            manifest=manifest,
        )

    async def _validate_artifact_ref(self, template_id: str, artifact: dict[str, Any]) -> list[TemplatePackValidationIssue]:
        issues: list[TemplatePackValidationIssue] = []
        key = str(artifact.get("key") or "")
        path = str(artifact.get("path") or "")
        if not key:
            issues.append(TemplatePackValidationIssue(code="artifact_key_missing", field_name="artifacts.key", severity="block", message="Artifact key is required."))
        if not path:
            issues.append(TemplatePackValidationIssue(code="artifact_path_missing", field_name="artifacts.path", severity="block", message="Artifact path is required."))

        if key == MEMORY_KEY:
            content = str(artifact.get("content") or "")
            if not content:
                stored = await self._repo.get_template_artifact(template_id, str(artifact.get("storage_key") or key))
                if stored:
                    content = stored.content or ""
            if content and self._looks_like_transcript(content):
                issues.append(TemplatePackValidationIssue(
                    code="memory_transcript",
                    field_name="artifacts.content",
                    severity="block",
                    message=".memory.md must not read like a raw transcript.",
                ))
            if content and not self._has_memory_sections(content):
                issues.append(TemplatePackValidationIssue(
                    code="memory_sections",
                    field_name="artifacts.content",
                    severity="block",
                    message=".memory.md requires a short execution-summary / decision-log structure.",
                ))
        return issues

    def _validate_paths(self, manifest: dict[str, Any], changed_files: list[str], *, mode: str) -> list[TemplatePackValidationIssue]:
        issues: list[TemplatePackValidationIssue] = []
        allowed_paths = [self._normalize_path(path) for path in manifest.get("allowed_paths") or []]
        forbidden_paths = [self._normalize_path(path) for path in manifest.get("forbidden_paths") or []]
        for path in changed_files:
            if allowed_paths and not any(fnmatchcase(path, pattern) for pattern in allowed_paths):
                issues.append(TemplatePackValidationIssue(
                    code="path_not_allowed",
                    field_name="path_guardrails",
                    severity="block",
                    message=f"Path '{path}' is outside the allowed paths.",
                    details={"allowed_paths": allowed_paths},
                ))
            if any(fnmatchcase(path, pattern) for pattern in forbidden_paths):
                issues.append(TemplatePackValidationIssue(
                    code="path_forbidden",
                    field_name="path_guardrails",
                    severity="block",
                    message=f"Path '{path}' is forbidden by the manifest.",
                    details={"forbidden_paths": forbidden_paths},
                ))
            if mode == "normal" and self._is_forbidden_runtime_path(path):
                issues.append(TemplatePackValidationIssue(
                    code="normal_run_forbidden_path",
                    field_name="path_guardrails",
                    severity="block",
                    message=f"Normal runs cannot modify '{path}'.",
                ))
        return issues

    async def _resolve_artifact(self, template_id: str, ref: dict[str, Any]) -> dict[str, Any] | None:
        storage_key = str(ref.get("storage_key") or ref.get("key") or "")
        artifact = None
        if storage_key:
            artifact = await self._repo.get_template_artifact(template_id, storage_key)
        if not artifact and ref.get("key") == OVERRIDE_AGENTS_KEY:
            scoped_key = f"{OVERRIDE_AGENTS_KEY}#{ref.get('scope_path') or ref.get('path') or ''}".rstrip("#")
            artifact = await self._repo.get_template_artifact(template_id, scoped_key)
        if not artifact:
            artifact = await self._repo.get_template_artifact(template_id, str(ref.get("key") or ""))
        if not artifact:
            return None
        if artifact.artifact_key == OVERRIDE_AGENTS_KEY:
            artifact = replace(artifact, artifact_key=OVERRIDE_AGENTS_KEY)
        elif artifact.artifact_key.startswith(f"{OVERRIDE_AGENTS_KEY}#"):
            artifact = replace(artifact, artifact_key=OVERRIDE_AGENTS_KEY)
        return {
            "key": ref.get("key") or artifact.artifact_key,
            "artifact_key": artifact.artifact_key,
            "content": artifact.content,
            "content_type": artifact.content_type,
            "uri": artifact.uri,
            "version": artifact.version,
            "scope_path": ref.get("scope_path") or ref.get("path"),
            "description": ref.get("description", ""),
            "metadata": artifact.metadata_,
        }

    def _root_agents_content(self, manifest: TemplatePackManifestV0) -> str:
        return (
            f"# {manifest.name}\n\n"
            "## Execution Summary\n"
            f"- Template: {manifest.id}\n"
            f"- Stack: {' + '.join(manifest.stack.get('name') or [])}\n"
            f"- Package manager: {manifest.stack.get('package_manager', 'pnpm')}\n\n"
            "## Decision Log\n"
            "- Keep the registry read-only.\n"
            "- Resolve overrides from shallow to deep scope.\n"
        )

    def _override_content(self, scope: str, note: str) -> str:
        return (
            f"# AGENTS Override - {scope}\n\n"
            "## Execution Summary\n"
            f"- Scope: {scope}\n"
            f"- Note: {note}\n\n"
            "## Decision Log\n"
            f"- {note}\n"
        )

    def _looks_like_transcript(self, content: str) -> bool:
        lowered = content.lower()
        return any(marker in lowered for marker in ("user:", "assistant:", "system:", "prompt:", "transcript"))

    def _has_memory_sections(self, content: str) -> bool:
        lowered = content.lower()
        return "execution summary" in lowered and "decision log" in lowered

    def _normalize_path(self, path: str) -> str:
        raw = str(path or "").strip()
        if raw in {"", ".", "./"}:
            return "."
        return Path(raw).as_posix().lstrip("./")

    def _is_forbidden_runtime_path(self, path: str) -> bool:
        normalized = self._normalize_path(path)
        return normalized.startswith(".karkhana/") or normalized == ".karkhana" or "/verification/" in normalized or normalized.startswith("verification/")

    def _path_matches_scope(self, target_path: str, scope_path: str) -> bool:
        normalized_scope = self._normalize_path(scope_path)
        if not normalized_scope or normalized_scope == ".":
            return True
        normalized_target = self._normalize_path(target_path)
        if normalized_target == ".":
            return True
        return normalized_target == normalized_scope or normalized_target.startswith(f"{normalized_scope}/")

    def _scope_depth(self, scope_path: str) -> int:
        normalized = self._normalize_path(scope_path)
        if not normalized or normalized == ".":
            return 0
        return len([part for part in normalized.split("/") if part])


def get_service() -> TemplatePackService:
    return TemplatePackService()
