from __future__ import annotations

"""Blueprint policy validation for the factory control plane.

The MVP keeps policy evaluation in Python so the factory-run path can validate
blueprints without any OPA/Rego runtime dependency. A future OpaPolicyEngine
can implement the same PolicyEngine.validate_blueprint() contract and be
selected by configuration later without changing callers.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from backend.app.repository import ProjectTwin, TemplatePack, utcnow


RING_0_READONLY = "ring_0_readonly"
RING_1_SCOPED_EXECUTION = "ring_1_scoped_execution"
RING_2_TOOL_INTEGRATION = "ring_2_tool_integration"
RING_3_HIGH_RISK_APPROVAL = "ring_3_high_risk_approval"

PERMISSION_RINGS = (
    RING_0_READONLY,
    RING_1_SCOPED_EXECUTION,
    RING_2_TOOL_INTEGRATION,
    RING_3_HIGH_RISK_APPROVAL,
)

KNOWN_WORKER_CAPABILITIES = frozenset({
    "repo_index",
    "architecture_dossier",
    "gap_analysis",
    "build_task_plan",
    "agent_branch_work",
    "test_verify",
    "sync_remote_state",
    "graphify_read",
    "graphify_update",
    "file_edit_scoped",
    "shell_scoped",
    "external_tool_integration",
    "deploy_production",
    "destructive_db",
    "secrets_write",
    "production_mutation",
    "broad_shell_access",
})

OPENCODE_SERVER_REQUIRED_CAPABILITIES = frozenset({
    "permission_guard",
    "circuit_breaker",
    "litellm_proxy",
    "diff_api",
    "verification_runner",
    "graphify_update",
})

LIMITED_ENGINES = frozenset({"opencode", "openclaude", "codex"})


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _from_iso(value: datetime | str | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _copy_list(value: list[str] | tuple[str, ...] | None) -> list[str]:
    if not value:
        return []
    return [str(item) for item in value]


@dataclass(slots=True)
class WorkerPermissionProfile:
    ring: str
    allowed_capabilities: list[str] = field(default_factory=list)
    tool_integrations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkerPermissionProfile":
        return cls(
            ring=data.get("ring"),
            allowed_capabilities=_copy_list(data.get("allowed_capabilities")),
            tool_integrations=_copy_list(data.get("tool_integrations")),
            notes=_copy_list(data.get("notes")),
        )


def blueprint_permission_profile_to_worker_policy(
    profile: WorkerPermissionProfile,
) -> dict[str, Any]:
    ring = profile.ring
    if ring == RING_0_READONLY:
        return {
            "allow_file_edits": False,
            "allow_shell_commands": [],
            "deny_patterns": ["rm -rf /", "del /s /q C:\\", "format ", "shutdown", "reboot"],
            "notes": ["Read-only inspection: no file edits, no shell commands."],
        }
    if ring == RING_1_SCOPED_EXECUTION:
        return {
            "allow_file_edits": True,
            "allow_shell_commands": [
                "git", "npm test", "npm run", "python -m pytest",
                "cargo test", "go test", "graphify",
            ],
            "deny_patterns": [
                "rm -rf /", "del /s /q C:\\", "format ", "shutdown", "reboot",
                "curl", "wget", "Invoke-WebRequest",
            ],
            "notes": ["Scoped execution: file edits allowed, shell restricted to test/graphify commands."],
        }
    if ring == RING_2_TOOL_INTEGRATION:
        return {
            "allow_file_edits": True,
            "allow_shell_commands": [
                "git", "npm", "python", "cargo", "go", "graphify",
                "aws", "docker", "kubectl",
            ],
            "deny_patterns": [
                "rm -rf /", "del /s /q C:\\", "shutdown", "reboot",
                "git push --force", "npm publish",
            ],
            "notes": ["Tool integration: broader shell access for declared tools."],
        }
    if ring == RING_3_HIGH_RISK_APPROVAL:
        return {
            "allow_file_edits": True,
            "allow_shell_commands": ["*"],
            "deny_patterns": ["rm -rf /", "del /s /q C:\\"],
            "notes": ["High-risk approval: unrestricted shell, all operations subject to human approval."],
        }
    return {
        "allow_file_edits": True,
        "allow_shell_commands": ["git", "npm test", "npm run", "python -m pytest", "cargo test", "go test"],
        "deny_patterns": ["rm -rf /", "del /s /q C:\\", "format ", "shutdown", "reboot"],
        "notes": ["Default scoped execution policy."],
    }


def validate_engine_for_autonomy_level(engine: str, autonomy_level: str) -> None:
    if autonomy_level in ("autonomous_development", "full_autopilot") and engine in LIMITED_ENGINES:
        raise ValueError(
            f"Engine '{engine}' is a limited fallback mode and is not valid for "
            f"autonomy level '{autonomy_level}'. High-autonomy Factory Runs require "
            f"an opencode-server engine or equivalent that provides: "
            f"{', '.join(sorted(OPENCODE_SERVER_REQUIRED_CAPABILITIES))}."
        )


def validate_worker_capabilities_for_autonomy(
    worker_capabilities: list[str],
    autonomy_level: str,
    *,
    worker_name: str = "unknown",
) -> list[str]:
    missing: list[str] = []
    if autonomy_level in ("autonomous_development", "full_autopilot"):
        for cap in OPENCODE_SERVER_REQUIRED_CAPABILITIES:
            if cap not in worker_capabilities:
                missing.append(cap)
    return missing


@dataclass(slots=True)
class ProjectBlueprint:
    blueprint_id: str
    project_id: str
    template_id: str
    template_version: str
    target_stack: list[str] = field(default_factory=list)
    files_or_modules: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    build_steps: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    permission_profile: WorkerPermissionProfile = field(
        default_factory=lambda: WorkerPermissionProfile(ring=RING_1_SCOPED_EXECUTION)
    )
    graphify_requirements: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = _iso(self.created_at)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectBlueprint":
        permission_profile = data.get("permission_profile") or {}
        if isinstance(permission_profile, WorkerPermissionProfile):
            permission_obj = permission_profile
        else:
            permission_obj = WorkerPermissionProfile.from_dict(permission_profile)
        return cls(
            blueprint_id=str(data.get("blueprint_id") or ""),
            project_id=str(data.get("project_id") or ""),
            template_id=str(data.get("template_id") or ""),
            template_version=str(data.get("template_version") or ""),
            target_stack=_copy_list(data.get("target_stack")),
            files_or_modules=_copy_list(data.get("files_or_modules")),
            dependencies=_copy_list(data.get("dependencies")),
            build_steps=_copy_list(data.get("build_steps")),
            verification_commands=_copy_list(data.get("verification_commands")),
            required_capabilities=_copy_list(data.get("required_capabilities")),
            permission_profile=permission_obj,
            graphify_requirements=dict(data.get("graphify_requirements") or {}),
            created_at=_from_iso(data.get("created_at")) or utcnow(),
        )


@dataclass(slots=True)
class PolicyIssue:
    code: str
    message: str
    severity: str
    field_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PolicyResult:
    status: str
    issues: list[PolicyIssue] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)
    executable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "issues": [issue.to_dict() for issue in self.issues],
            "feedback": list(self.feedback),
            "executable": self.executable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyResult":
        return cls(
            status=str(data.get("status") or "pass"),
            issues=[
                PolicyIssue(
                    code=str(issue.get("code") or "unknown"),
                    message=str(issue.get("message") or ""),
                    severity=str(issue.get("severity") or "warn"),
                    field_name=issue.get("field_name") or issue.get("field"),
                    details=dict(issue.get("details") or {}),
                )
                for issue in data.get("issues") or []
            ],
            feedback=[str(item) for item in (data.get("feedback") or [])],
            executable=bool(data.get("executable", True)),
        )


class PolicyBlockedError(Exception):
    def __init__(self, policy_result: PolicyResult) -> None:
        self.policy_result = policy_result
        self.feedback = list(policy_result.feedback)
        super().__init__("Blueprint blocked by policy")

    @property
    def detail(self) -> dict[str, Any]:
        return {
            "error": "policy_blocked",
            "message": "Blueprint blocked by policy",
            "policy_result": self.policy_result.to_dict(),
            "feedback": list(self.feedback),
        }


class PolicyEngine(ABC):
    @abstractmethod
    def validate_blueprint(
        self,
        blueprint: ProjectBlueprint,
        *,
        project: ProjectTwin | None = None,
        template: TemplatePack | None = None,
    ) -> PolicyResult:
        raise NotImplementedError


class PythonPolicyEngine(PolicyEngine):
    def validate_blueprint(
        self,
        blueprint: ProjectBlueprint,
        *,
        project: ProjectTwin | None = None,
        template: TemplatePack | None = None,
    ) -> PolicyResult:
        issues: list[PolicyIssue] = []

        self._require_non_empty_string(blueprint.blueprint_id, "blueprint_id", issues)
        self._require_non_empty_string(blueprint.project_id, "project_id", issues)
        self._require_non_empty_string(blueprint.template_id, "template_id", issues)
        self._require_non_empty_string(blueprint.template_version, "template_version", issues)

        self._require_list(blueprint.target_stack, "target_stack", issues, warn_if_empty=True)
        self._require_list(blueprint.files_or_modules, "files_or_modules", issues, warn_if_empty=True)
        self._require_list(blueprint.dependencies, "dependencies", issues)
        self._require_list(blueprint.build_steps, "build_steps", issues, required=True)
        self._require_list(blueprint.verification_commands, "verification_commands", issues, warn_if_empty=True)
        self._require_list(blueprint.required_capabilities, "required_capabilities", issues)
        self._require_dict(blueprint.graphify_requirements, "graphify_requirements", issues)
        self._require_datetime(blueprint.created_at, "created_at", issues)
        self._require_permission_profile(blueprint.permission_profile, issues)

        if project is not None:
            self._match_field(blueprint.project_id, project.id, "project_id", "project twin", issues)
        if template is not None:
            self._match_field(blueprint.template_id, template.template_id, "template_id", "template pack", issues)
            self._match_field(
                blueprint.template_version,
                template.version,
                "template_version",
                "template pack",
                issues,
            )

        if not blueprint.verification_commands:
            issues.append(PolicyIssue(
                code="missing_verification_commands",
                field_name="verification_commands",
                severity="warn",
                message="Verification commands are empty.",
                details={"suggestion": "Add verification commands so the worker can prove the change."},
            ))

        graphify_requirements = blueprint.graphify_requirements or {}
        post_task = _copy_list(graphify_requirements.get("post_task")) if isinstance(graphify_requirements, dict) else []
        if not post_task:
            issues.append(PolicyIssue(
                code="missing_graphify_post_update",
                field_name="graphify_requirements.post_task",
                severity="warn",
                message="Graphify post-task update is missing.",
                details={"suggestion": "Add graphify update . after the task finishes."},
            ))

        if not blueprint.target_stack:
            issues.append(PolicyIssue(
                code="missing_target_stack",
                field_name="target_stack",
                severity="warn",
                message="Target stack is empty.",
                details={"suggestion": "Populate target_stack so the execution contract is specific."},
            ))

        if self._is_broad_scope(blueprint.files_or_modules):
            issues.append(PolicyIssue(
                code="broad_file_scope",
                field_name="files_or_modules",
                severity="warn",
                message="File/module scope is broad or unspecified.",
                details={"suggestion": "Narrow files_or_modules to the smallest practical scope."},
            ))

        permission_profile = blueprint.permission_profile
        if self._uses_high_risk_action(blueprint.build_steps, blueprint.verification_commands):
            if permission_profile.ring != RING_3_HIGH_RISK_APPROVAL:
                issues.append(PolicyIssue(
                    code="high_risk_action",
                    field_name="build_steps",
                    severity="block",
                    message="High-risk actions require ring_3_high_risk_approval.",
                    details={
                        "suggestion": (
                            "Revise blueprint: remove production deployment or request "
                            "ring_3_high_risk_approval; add verification commands."
                        )
                    },
                ))

        allowed_capabilities = set(KNOWN_WORKER_CAPABILITIES)
        allowed_capabilities.update(permission_profile.allowed_capabilities)
        allowed_capabilities.update(permission_profile.tool_integrations)
        unknown_capabilities = [
            capability
            for capability in blueprint.required_capabilities
            if capability not in allowed_capabilities
        ]
        if unknown_capabilities:
            issues.append(PolicyIssue(
                code="unsupported_capabilities",
                field_name="required_capabilities",
                severity="block",
                message="Required capabilities are outside the known worker capability set.",
                details={
                    "capabilities": unknown_capabilities,
                    "suggestion": (
                        "Declare the capability in the permission profile or remove the unsupported requirement."
                    ),
                },
            ))

        status = "pass"
        if any(issue.severity == "block" for issue in issues):
            status = "block"
        elif any(issue.severity == "warn" for issue in issues):
            status = "warn"

        feedback = self._build_feedback(status, issues)
        return PolicyResult(
            status=status,
            issues=issues,
            feedback=feedback,
            executable=status != "block",
        )

    @staticmethod
    def _require_non_empty_string(value: Any, field_name: str, issues: list[PolicyIssue]) -> None:
        if not isinstance(value, str) or not value.strip():
            issues.append(PolicyIssue(
                code=f"invalid_{field_name}",
                field_name=field_name,
                severity="block",
                message=f"{field_name} must be a non-empty string.",
            ))

    @staticmethod
    def _require_list(
        value: Any,
        field_name: str,
        issues: list[PolicyIssue],
        *,
        required: bool = False,
        warn_if_empty: bool = False,
    ) -> None:
        if not isinstance(value, list):
            issues.append(PolicyIssue(
                code=f"invalid_{field_name}",
                field_name=field_name,
                severity="block",
                message=f"{field_name} must be a list.",
            ))
            return
        if required and not value:
            issues.append(PolicyIssue(
                code=f"empty_{field_name}",
                field_name=field_name,
                severity="block",
                message=f"{field_name} cannot be empty.",
            ))
        elif warn_if_empty and not value:
            issues.append(PolicyIssue(
                code=f"empty_{field_name}",
                field_name=field_name,
                severity="warn",
                message=f"{field_name} is empty.",
            ))

    @staticmethod
    def _require_dict(value: Any, field_name: str, issues: list[PolicyIssue]) -> None:
        if not isinstance(value, dict):
            issues.append(PolicyIssue(
                code=f"invalid_{field_name}",
                field_name=field_name,
                severity="block",
                message=f"{field_name} must be a dict.",
            ))

    @staticmethod
    def _require_datetime(value: Any, field_name: str, issues: list[PolicyIssue]) -> None:
        if not isinstance(value, datetime):
            issues.append(PolicyIssue(
                code=f"invalid_{field_name}",
                field_name=field_name,
                severity="block",
                message=f"{field_name} must be a datetime.",
            ))

    @staticmethod
    def _require_permission_profile(value: Any, issues: list[PolicyIssue]) -> None:
        if not isinstance(value, WorkerPermissionProfile):
            issues.append(PolicyIssue(
                code="invalid_permission_profile",
                field_name="permission_profile",
                severity="block",
                message="permission_profile must be a WorkerPermissionProfile.",
            ))
            return
        if value.ring not in PERMISSION_RINGS:
            issues.append(PolicyIssue(
                code="invalid_permission_ring",
                field_name="permission_profile.ring",
                severity="block",
                message="permission_profile ring is not recognized.",
                details={"ring": value.ring},
            ))

    @staticmethod
    def _match_field(
        provided: str,
        expected: str,
        field_name: str,
        source_name: str,
        issues: list[PolicyIssue],
    ) -> None:
        if provided != expected:
            issues.append(PolicyIssue(
                code=f"mismatched_{field_name}",
                field_name=field_name,
                severity="block",
                message=f"{field_name} does not match the loaded {source_name}.",
                details={"expected": expected, "provided": provided},
            ))

    @staticmethod
    def _is_broad_scope(files_or_modules: list[str]) -> bool:
        if not files_or_modules:
            return True
        broad_markers = {".", "./", "*", "**", "/", "\\", "all", "everything"}
        for item in files_or_modules:
            normalized = item.strip().lower()
            if not normalized:
                return True
            if normalized in broad_markers:
                return True
            if normalized.endswith("/**") or normalized.endswith("\\**"):
                return True
            if "*" in normalized and normalized != "*":
                return True
        return False

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

    @staticmethod
    def _build_feedback(status: str, issues: list[PolicyIssue]) -> list[str]:
        messages: list[str] = []
        for issue in issues:
            if issue.severity == "block":
                suggestion = issue.details.get("suggestion") if issue.details else None
                if suggestion and suggestion not in messages:
                    messages.append(str(suggestion))
            elif issue.severity == "warn":
                suggestion = issue.details.get("suggestion") if issue.details else None
                if suggestion and suggestion not in messages:
                    messages.append(str(suggestion))

        if status == "block" and not messages:
            messages.append("Revise blueprint to remove blocked policy issues.")
        return messages
