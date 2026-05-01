from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any

from backend.app.config import settings
from backend.app.repository import (
    AgentRun,
    CodeIndexArtifact,
    GitHubInstallation,
    Idea,
    ProjectCommit,
    ProjectTwin,
    Report,
    WorkItem,
    get_repository,
    utcnow,
)
from backend.app.services.autonomy import HIGH_AUTONOMY_LEVELS
from backend.app.services.factory_tracking import collect_factory_run_bundle, refresh_factory_run_tracking_manifest
from backend.app.services.factory_tracking import normalize_token_economy
from backend.app.services.factory_run_ledger import extract_compact_ledger_context, validate_ledger_metadata
from backend.app.services.github_app import GitHubAppService
from backend.app.services.worker_sqs import WorkerSqsPublisher

CLAIMABLE_STATUSES = {"queued", "waiting_for_machine", "failed_retryable"}
OPEN_JOB_STATUSES = {"queued", "waiting_for_machine", "failed_retryable", "claimed", "running"}
TERMINAL_STATUSES = {"completed", "cancelled", "failed_terminal"}
DUPLICATE_WORK_MATCH_STATUSES = OPEN_JOB_STATUSES | {"completed"}
DEPLOY_HINT_FILES = {
    "Dockerfile": "docker",
    "docker-compose.yml": "docker-compose",
    "docker-compose.yaml": "docker-compose",
    "amplify.yml": "amplify",
    "amplify.yaml": "amplify",
    "serverless.yml": "serverless",
    "serverless.yaml": "serverless",
    "vercel.json": "vercel",
    "netlify.toml": "netlify",
    "render.yaml": "render",
    "fly.toml": "fly.io",
    "Procfile": "procfile",
    "template.yaml": "cloudformation",
    "template.yml": "cloudformation",
}
_VERIFICATION_FAILURE_STATUSES = {"failed", "timed_out", "blocked"}
_VERIFICATION_SUCCESS_STATUSES = {"passed", "succeeded", "success", "completed", "ok"}
_VERIFICATION_RESULT_KEYS = ("verification_results", "verification_checks", "verification_evidence")


def _normalize_index_path(path: Any) -> str:
    return str(path or "").replace("\\", "/")


def _job_status_category(status: str) -> str:
    if status == "completed":
        return "completed"
    if status == "cancelled":
        return "cancelled"
    if status.startswith("failed"):
        return "failed"
    if status in {"claimed", "running"}:
        return "running"
    return "queued"


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def _normalize_command_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list | tuple | set):
        values = list(value)
    else:
        values = [value]
    commands: list[str] = []
    for item in values:
        command = str(item).strip()
        if command and command not in commands:
            commands.append(command)
    return commands


def _normalize_job_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(payload or {})
    if "verification_commands" in data or "test_commands" in data:
        commands_source = data.get("verification_commands")
        if commands_source is None:
            commands_source = data.get("test_commands")
        data["verification_commands"] = _normalize_command_list(commands_source)
        data.pop("test_commands", None)
    return data


def _verification_commands_for_payload(payload: dict[str, Any] | None) -> list[str]:
    payload = payload or {}
    return _normalize_command_list(payload.get("verification_commands") or payload.get("test_commands"))


def _verification_result_entries(result: dict[str, Any]) -> list[dict[str, Any]]:
    for key in _VERIFICATION_RESULT_KEYS:
        raw = result.get(key)
        if isinstance(raw, dict):
            entries: list[dict[str, Any]] = []
            for command, value in raw.items():
                if isinstance(value, dict):
                    entry = dict(value)
                    entry.setdefault("command", command)
                else:
                    entry = {"command": command, "status": value}
                entries.append(entry)
            return entries
        if isinstance(raw, list):
            entries = [dict(item) for item in raw if isinstance(item, dict)]
            if entries:
                return entries
    return []


def _normalize_verification_status(value: Any) -> str:
    status = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if status in {"timedout", "timeout"}:
        return "timed_out"
    return status


def _verification_failure_reason(*, payload: dict[str, Any], result: dict[str, Any], job_type: str) -> str | None:
    if job_type == "repo_index":
        return None
    commands = _verification_commands_for_payload(payload)
    if not commands:
        return None

    entries = _verification_result_entries(result)
    if not entries:
        if result.get("tests_passed") is False:
            return "Required verification command failed."
        return "Required verification evidence is missing."

    evidence_by_command: dict[str, list[str]] = {}
    for entry in entries:
        command = str(entry.get("command") or entry.get("name") or entry.get("check") or "").strip()
        if not command:
            continue
        status = _normalize_verification_status(entry.get("status") or entry.get("state") or entry.get("result"))
        evidence_by_command.setdefault(command, []).append(status)

    missing_commands = [command for command in commands if command not in evidence_by_command]
    if missing_commands:
        return f"Required verification evidence is missing for: {', '.join(missing_commands)}"

    for command in commands:
        statuses = evidence_by_command.get(command, [])
        if not statuses:
            return f"Required verification evidence is missing for: {command}"
        failing = next((status for status in statuses if status in _VERIFICATION_FAILURE_STATUSES), None)
        if failing:
            return f"Verification command '{command}' reported status '{failing}'."
        if not any(status in _VERIFICATION_SUCCESS_STATUSES for status in statuses):
            return f"Verification command '{command}' did not report a passing status."

    if result.get("tests_passed") is False:
        return "Required verification command failed."
    return None


def _draft_pr_metadata_from_sources(*sources: dict[str, Any] | None) -> dict[str, Any]:
    draft_pr: dict[str, Any] = {}
    for source in sources:
        source = source or {}
        nested = source.get("draft_pr")
        if isinstance(nested, dict):
            draft_pr.update({key: value for key, value in nested.items() if value is not None})
        for key in (
            "draft_pr_url",
            "draft_pr_number",
            "draft_pr_title",
            "draft_pr_state",
            "draft_pr_branch_name",
            "draft_pr_head_branch",
            "draft_pr_base_branch",
            "pull_request_url",
            "pr_url",
        ):
            if source.get(key) is not None:
                draft_pr[key] = source.get(key)
    return draft_pr


def _job_draft_pr_metadata(item: WorkItem) -> dict[str, Any]:
    return _draft_pr_metadata_from_sources(item.payload, item.result)


def _job_draft_pr_title(item: WorkItem, result: dict[str, Any]) -> str:
    payload = item.payload or {}
    candidates = [
        result.get("commit_message"),
        payload.get("commit_message"),
        payload.get("task"),
        payload.get("title"),
        payload.get("goal"),
        payload.get("summary"),
        payload.get("description"),
    ]
    for candidate in candidates:
        title = str(candidate or "").strip()
        if title:
            return title
    return f"Idea Refinery job {item.id}"


def _job_draft_pr_verification_summary(result: dict[str, Any]) -> str:
    parts: list[str] = []
    tests_passed = result.get("tests_passed")
    if tests_passed is not None:
        parts.append(f"tests_passed={bool(tests_passed)}")
    entries = _verification_result_entries(result)
    if entries:
        rendered: list[str] = []
        for entry in entries[:5]:
            command = str(entry.get("command") or entry.get("name") or entry.get("check") or "verification").strip()
            status = _normalize_verification_status(entry.get("status") or entry.get("state") or entry.get("result"))
            rendered.append(f"{command}: {status or 'unknown'}")
        if len(entries) > 5:
            rendered.append(f"...and {len(entries) - 5} more")
        parts.append("verification_results=" + "; ".join(rendered))
    elif result.get("summary"):
        parts.append(f"summary={str(result.get('summary')).strip()}")
    return "; ".join(parts) if parts else "No verification summary was provided."


def _job_draft_pr_graphify_status(payload: dict[str, Any], result: dict[str, Any]) -> str:
    graphify_required = any("graphify update" in command for command in _verification_commands_for_payload(payload))
    if result.get("graphify_updated"):
        return "graphify_updated=True"
    if graphify_required:
        return "graphify_updated=False (required)"
    return "graphify_updated=False"


def _job_draft_pr_body(item: WorkItem, project: ProjectTwin, result: dict[str, Any], logs: str = "") -> str:
    branch_name = result.get("branch_name") or item.branch_name or (item.payload or {}).get("branch_name") or (item.payload or {}).get("branch")
    commit_sha = result.get("commit_sha") or "unknown"
    payload = item.payload or {}
    lines = [
        f"Job ID: {item.id}",
        f"Branch: {branch_name or 'unknown'}",
        f"Base branch: {project.default_branch}",
        f"Commit: {commit_sha}",
        f"Verification summary: {_job_draft_pr_verification_summary(result)}",
        f"Graphify status: {_job_draft_pr_graphify_status(payload, result)}",
        "Logs note: completion logs are stored on the job record.",
        "",
        "Human approval required before merge.",
    ]
    if logs:
        lines.insert(6, f"Completion logs: {logs[-400:].strip()}")
    return "\n".join(lines)


def _should_create_draft_pull_request(item: WorkItem, payload: dict[str, Any], result: dict[str, Any], draft_pr: dict[str, Any]) -> bool:
    if item.job_type == "repo_index":
        return False
    if (payload.get("autonomy_level") or "") not in HIGH_AUTONOMY_LEVELS:
        return False
    if draft_pr:
        return False
    if not result.get("branch_name") or not result.get("commit_sha"):
        return False
    return True


async def _create_draft_pull_request(
    *,
    item: WorkItem,
    project: ProjectTwin,
    result: dict[str, Any],
    logs: str = "",
) -> dict[str, Any]:
    branch_name = result.get("branch_name") or item.branch_name or (item.payload or {}).get("branch_name") or (item.payload or {}).get("branch")
    if not branch_name:
        raise RuntimeError("missing branch name for draft pull request")
    title = _job_draft_pr_title(item, result)
    body = _job_draft_pr_body(item, project, result, logs)
    github = GitHubAppService()
    pr = await github.create_draft_pull_request(
        installation_id=project.installation_id,
        owner=project.owner,
        repo_name=project.repo,
        title=title,
        head_branch=branch_name,
        base_branch=project.default_branch,
        body=body,
    )
    html_url = pr.get("html_url") or pr.get("url") or ""
    draft_pr = {
        "url": html_url,
        "html_url": html_url,
        "pull_request_url": html_url,
        "number": pr.get("number"),
        "state": pr.get("state") or "",
        "draft": bool(pr.get("draft", True)),
        "title": title,
        "body": body,
        "branch_name": branch_name,
        "head_branch": branch_name,
        "base_branch": project.default_branch,
        "commit_sha": result.get("commit_sha"),
        "job_id": item.id,
    }
    return draft_pr


def job_to_jsonable(item: WorkItem, *, include_claim_token: bool = False) -> dict[str, Any]:
    """Return a WorkItem with explicit local-worker execution inspection fields."""
    data = to_jsonable(item)
    if not include_claim_token:
        data.pop("claim_token", None)
    heartbeat = item.heartbeat_at or item.claimed_at or item.updated_at
    is_active = item.status in {"claimed", "running"}
    is_stale = bool(
        is_active
        and heartbeat
        and (utcnow() - heartbeat).total_seconds() > item.timeout_seconds
    )
    data["execution_state"] = {
        "status": item.status,
        "category": _job_status_category(item.status),
        "priority": item.priority,
        "retry_count": item.retry_count,
        "is_claimable": item.status in CLAIMABLE_STATUSES,
        "is_active": is_active,
        "is_terminal": item.status in TERMINAL_STATUSES,
        "is_stale": is_stale,
        "run_after": item.run_after.isoformat() if item.run_after else None,
        "timeout_seconds": item.timeout_seconds,
    }
    data["worker_state"] = {
        "worker_id": item.worker_id,
        "claimed_at": item.claimed_at.isoformat() if item.claimed_at else None,
        "heartbeat_at": item.heartbeat_at.isoformat() if item.heartbeat_at else None,
        "last_seen_at": heartbeat.isoformat() if heartbeat else None,
        "has_claim_token": bool(item.claim_token),
    }
    data["logs_tail"] = item.logs[-4000:] if item.logs else ""
    data["has_result"] = item.result is not None
    data["has_error"] = bool(item.error)
    if item.agent_run_id:
        data["agent_run_id"] = item.agent_run_id
    payload = item.payload or {}
    result = item.result or {}
    engine = (result.get("engine") if isinstance(result, dict) else None) or payload.get("engine")
    model = (result.get("model") if isinstance(result, dict) else None) or payload.get("model") or payload.get("role_model")
    agent_name = (
        (result.get("agent_name") if isinstance(result, dict) else None)
        or (result.get("agent") if isinstance(result, dict) else None)
        or payload.get("agent")
        or payload.get("agent_name")
        or payload.get("role")
    )
    command = (result.get("command") if isinstance(result, dict) else None) or payload.get("command") or _worker_command_example(item)
    branch_name = item.branch_name or (result.get("branch_name") if isinstance(result, dict) else None) or payload.get("branch") or payload.get("branch_name")
    verification_commands = _verification_commands_for_payload(payload)
    prompt = _work_item_prompt(item)
    data["engine"] = engine
    data["model"] = model
    data["agent_name"] = agent_name
    data["command"] = command
    data["branch_name"] = branch_name
    data["verification_commands"] = verification_commands
    draft_pr = _job_draft_pr_metadata(item)
    if draft_pr:
        data["draft_pr"] = draft_pr
    data["opencode"] = {
        "engine": engine,
        "model": model,
        "agent": agent_name,
        "command": command,
        "branch_name": branch_name,
        "has_prompt": bool(prompt),
        "prompt_preview": prompt[:500] if prompt else "",
    }
    if item.error:
        data["debug_prompt"] = _debug_prompt(item)
    return data


def _work_item_prompt(item: WorkItem) -> str:
    payload = item.payload or {}
    prompt = payload.get("prompt") or payload.get("role_prompt") or payload.get("worker_prompt") or payload.get("codex_prompt")
    if prompt:
        return str(prompt)
    goal = payload.get("goal") or item.rationale
    return str(goal or "")


def _duplicate_work_keys(item: WorkItem) -> set[str]:
    payload = item.payload or {}
    keys = {
        key
        for key in (
            payload.get("duplicate_work_key"),
            item.idempotency_key,
            item.dedupe_hash,
        )
        if key
    }
    return keys


def _duplicate_work_detected(item: WorkItem) -> bool:
    payload = item.payload or {}
    result = item.result or {}
    token_economy = result.get("token_economy") if isinstance(result, dict) else {}
    return bool(
        payload.get("duplicate_work_detected")
        or payload.get("duplicate_work_key")
        or result.get("duplicate_work_detected")
        or (token_economy.get("duplicate_work_detected") if isinstance(token_economy, dict) else False)
    )


def _manifest_content_map(latest_index: CodeIndexArtifact | None) -> dict[str, str]:
    manifests: dict[str, str] = {}
    for manifest in (latest_index.manifests if latest_index else []):
        path = _normalize_index_path(manifest.get("path"))
        content = str(manifest.get("content") or "")
        if path and path not in manifests:
            manifests[path] = content
    return manifests


def _manifest_contents_by_name(latest_index: CodeIndexArtifact | None, name: str) -> list[tuple[str, str]]:
    return [
        (path, content)
        for path, content in _manifest_content_map(latest_index).items()
        if path.rsplit("/", 1)[-1] == name
    ]


def _has_manifest(latest_index: CodeIndexArtifact | None, name: str) -> bool:
    return bool(_manifest_contents_by_name(latest_index, name))


def _has_file_named(paths: set[str], *names: str) -> bool:
    return any(path.rsplit("/", 1)[-1] in names for path in paths)


def _detect_stack(latest_index: CodeIndexArtifact | None, project: ProjectTwin) -> list[str]:
    paths = {_normalize_index_path(entry.get("path")) for entry in (latest_index.file_inventory if latest_index else [])}
    stack: list[str] = []

    def add(value: str) -> None:
        if value not in stack:
            stack.append(value)

    if _has_manifest(latest_index, "package.json"):
        add("node")
        if any(path.endswith((".svelte", ".tsx", ".jsx")) for path in paths):
            add("frontend")
        if any(path.startswith(("frontend/", "app/", "pages/")) or "/routes/" in path for path in paths):
            add("web app")
    if _has_manifest(latest_index, "pyproject.toml") or _has_manifest(latest_index, "requirements.txt"):
        add("python")
        if any(path.startswith(("backend/", "app/", "src/")) for path in paths):
            add("api/backend")
    if _has_manifest(latest_index, "Cargo.toml"):
        add("rust")
    if _has_manifest(latest_index, "go.mod"):
        add("go")
    if any(path.startswith("worker-app/") for path in paths):
        add("worker app")
    if any(path.startswith("backend/") for path in paths):
        add("backend")
    if any(path.startswith("frontend/") for path in paths):
        add("frontend")
    if not stack and project.detected_stack:
        return list(project.detected_stack)
    return stack


def _parse_package_scripts(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except Exception:
        return {}
    scripts = parsed.get("scripts") or {}
    return scripts if isinstance(scripts, dict) else {}


def _detect_commands(latest_index: CodeIndexArtifact | None) -> tuple[list[str], list[str]]:
    test_commands: list[str] = list(dict.fromkeys((latest_index.test_commands if latest_index else [])))
    build_commands: list[str] = []

    def add(target: list[str], command: str) -> None:
        if command not in target:
            target.append(command)

    package_scripts_by_path = [
        (path, _parse_package_scripts(content))
        for path, content in _manifest_contents_by_name(latest_index, "package.json")
    ]
    for _path, package_scripts in package_scripts_by_path:
        if "test" in package_scripts:
            add(test_commands, "npm test")
        if "build" in package_scripts:
            add(build_commands, "npm run build")
        if "lint" in package_scripts:
            add(build_commands, "npm run lint")
        if "dev" in package_scripts and not build_commands:
            add(build_commands, "npm run dev")

    if _has_manifest(latest_index, "pyproject.toml") or _has_manifest(latest_index, "requirements.txt"):
        add(test_commands, "python -m pytest")
        if _has_manifest(latest_index, "requirements.txt"):
            add(build_commands, "python -m pip install -r requirements.txt")
    if _has_manifest(latest_index, "Cargo.toml"):
        add(test_commands, "cargo test")
        add(build_commands, "cargo build")
    if _has_manifest(latest_index, "go.mod"):
        add(test_commands, "go test ./...")
        add(build_commands, "go build ./...")
    if _has_manifest(latest_index, "Dockerfile"):
        add(build_commands, "docker build .")

    return test_commands[:6], build_commands[:6]


def _detect_route_hints(latest_index: CodeIndexArtifact | None) -> list[str]:
    if not latest_index:
        return []
    hints: list[str] = []
    seen_paths: set[str] = set()
    for entry in latest_index.route_map:
        path = _normalize_index_path(entry.get("path"))
        line = str(entry.get("line") or "")
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        hints.append(f"{path}: {line[:120]}")
        if len(hints) >= 6:
            break
    if hints:
        return hints
    inventory_paths = [_normalize_index_path(item.get("path")) for item in latest_index.file_inventory]
    for marker in ("app/", "pages/", "routes/", "src/app/", "src/pages/", "src/routes/", "api/"):
        match = next((path for path in inventory_paths if marker in path), None)
        if match:
            hints.append(match)
    return hints[:6]


def _detect_deploy_hints(latest_index: CodeIndexArtifact | None) -> list[str]:
    if not latest_index:
        return []
    paths = [_normalize_index_path(item.get("path")) for item in latest_index.file_inventory]
    hints: list[str] = []
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        if name in DEPLOY_HINT_FILES:
            hints.append(DEPLOY_HINT_FILES[name])
    if any(path.startswith(".github/workflows/") for path in paths):
        hints.append("github actions")
    if any(path.endswith(("infra/main.tf", ".tf")) for path in paths):
        hints.append("terraform")
    return list(dict.fromkeys(hints))[:6]


def _detect_dependency_risks(latest_index: CodeIndexArtifact | None) -> list[str]:
    if not latest_index:
        return []
    paths = {_normalize_index_path(item.get("path")) for item in latest_index.file_inventory}
    risks: list[str] = []

    def add(message: str) -> None:
        if message not in risks:
            risks.append(message)

    package_manifests = _manifest_contents_by_name(latest_index, "package.json")
    if package_manifests:
        if not _has_file_named(paths, "package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
            add("Node project has no lockfile in the index.")
        package_scripts = [scripts for _path, content in package_manifests if (scripts := _parse_package_scripts(content))]
        if not any(scripts.get("test") for scripts in package_scripts):
            add("package.json has no test script.")
    if _has_manifest(latest_index, "pyproject.toml") or _has_manifest(latest_index, "requirements.txt"):
        if not latest_index.test_commands:
            add("Python project has no obvious test command.")
    if _has_manifest(latest_index, "Cargo.toml") and not _has_file_named(paths, "Cargo.lock"):
        add("Rust project has no Cargo.lock in the index.")
    if _has_manifest(latest_index, "go.mod") and not _has_file_named(paths, "go.sum"):
        add("Go module has no go.sum in the index.")
    if latest_index.manifests and not latest_index.test_commands:
        add("Index did not discover a test command for this repo.")
    if any(path.endswith("Dockerfile") for path in paths) and not any(path.endswith(("package.json", "pyproject.toml", "Cargo.toml", "go.mod")) for path in paths):
        add("Dockerfile found without a clear application manifest.")
    return risks[:8]


def _summarize_package_manifests(latest_index: CodeIndexArtifact | None) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path, content in _manifest_content_map(latest_index).items():
        name = path.rsplit("/", 1)[-1]
        if name not in {"package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"}:
            continue
        summary: dict[str, Any] = {"path": path, "kind": name}
        if name == "package.json":
            scripts = _parse_package_scripts(content)
            summary["scripts"] = sorted(str(key) for key in scripts.keys())[:12]
            summary["has_test"] = bool(scripts.get("test"))
            summary["has_build"] = bool(scripts.get("build"))
        elif name in {"pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"}:
            summary["ecosystem"] = {
                "pyproject.toml": "python",
                "requirements.txt": "python",
                "Cargo.toml": "rust",
                "go.mod": "go",
            }[name]
        summaries.append(summary)
    return summaries[:8]


def _build_actionable_metadata(
    project: ProjectTwin,
    latest_index: CodeIndexArtifact | None,
    *,
    test_commands: list[str],
    build_commands: list[str],
    route_hints: list[str],
    deploy_hints: list[str],
    dependency_risks: list[str],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    todo_markers = latest_index.todos[:5] if latest_index else []
    next_action_hints: list[str] = []

    def add_hint(message: str) -> None:
        if message not in next_action_hints:
            next_action_hints.append(message)

    if freshness.get("state") == "stale":
        add_hint("Reindex before planning code changes.")
    if test_commands:
        add_hint(f"Validate with: {test_commands[0]}")
    else:
        add_hint("Identify or add a repeatable test command.")
    if build_commands:
        add_hint(f"Build with: {build_commands[0]}")
    if route_hints:
        add_hint("Use route hints to target UI/API entry points.")
    if deploy_hints:
        add_hint(f"Deployment surface detected: {', '.join(deploy_hints[:2])}.")
    if dependency_risks:
        add_hint("Resolve dependency/index risks before broad automation.")
    if todo_markers:
        add_hint("Review TODO/FIXME markers for quick next actions.")

    return {
        "package_manifests": _summarize_package_manifests(latest_index),
        "likely_test_commands": test_commands,
        "likely_build_commands": build_commands,
        "route_hints": route_hints,
        "deployment_hints": deploy_hints,
        "dependency_risks": dependency_risks,
        "todo_markers": todo_markers,
        "index_status": {
            "project_status": project.index_status,
            "freshness": freshness.get("state"),
            "last_indexed_commit": project.last_indexed_commit,
            "latest_known_commit": freshness.get("latest_commit_sha"),
            "is_stale": freshness.get("state") == "stale",
        },
        "next_action_hints": next_action_hints[:8],
    }


def _compute_index_freshness(project: ProjectTwin, latest_index: CodeIndexArtifact | None, commits: list[ProjectCommit]) -> dict[str, Any]:
    latest_commit = max(commits, key=lambda commit: commit.created_at) if commits else None
    if not latest_index:
        return {
            "state": "unknown",
            "reason": "No code index available yet.",
            "indexed_at": None,
            "latest_commit_at": latest_commit.created_at.isoformat() if latest_commit else None,
            "latest_commit_sha": latest_commit.commit_sha if latest_commit else None,
        }
    if latest_commit and latest_index.commit_sha != latest_commit.commit_sha:
        delta = latest_commit.created_at - latest_index.created_at
        age_hours = max(0, int(delta.total_seconds() // 3600))
        return {
            "state": "stale",
            "reason": f"Known commit {latest_commit.commit_sha[:7]} differs from indexed commit {latest_index.commit_sha[:7]} ({age_hours}h newer by record time).",
            "indexed_at": latest_index.created_at.isoformat(),
            "latest_commit_at": latest_commit.created_at.isoformat(),
            "latest_commit_sha": latest_commit.commit_sha,
            "indexed_commit_sha": latest_index.commit_sha,
        }
    if project.health_status == "remote_changed":
        return {
            "state": "stale",
            "reason": "Remote changes were detected; reindex recommended.",
            "indexed_at": latest_index.created_at.isoformat(),
            "latest_commit_at": latest_commit.created_at.isoformat() if latest_commit else None,
            "latest_commit_sha": latest_commit.commit_sha if latest_commit else None,
        }
    return {
        "state": "fresh",
        "reason": "Index matches the latest known commit.",
        "indexed_at": latest_index.created_at.isoformat(),
        "latest_commit_at": latest_commit.created_at.isoformat() if latest_commit else None,
        "latest_commit_sha": latest_commit.commit_sha if latest_commit else None,
    }


def summarize_project_twin(project: ProjectTwin, latest_index: CodeIndexArtifact | None, commits: list[ProjectCommit]) -> dict[str, Any]:
    test_commands, build_commands = _detect_commands(latest_index)
    route_hints = _detect_route_hints(latest_index)
    deploy_hints = _detect_deploy_hints(latest_index)
    dependency_risks = _detect_dependency_risks(latest_index)
    freshness = _compute_index_freshness(project, latest_index, commits)
    manifest_paths = [_normalize_index_path(m.get("path")) for m in (latest_index.manifests if latest_index else [])]
    missing_info: list[str] = []
    if not manifest_paths:
        missing_info.append("No manifests were indexed.")
    if not route_hints:
        missing_info.append("No route or app structure hints were detected.")
    if not deploy_hints:
        missing_info.append("No deployment hints were detected.")
    if not test_commands:
        missing_info.append("No test command was discovered.")

    status_fragments = [f"{freshness['state']} index"]
    if dependency_risks:
        status_fragments.append(f"{len(dependency_risks)} risks")
    if missing_info:
        status_fragments.append(f"{len(missing_info)} gaps")
    if latest_index and latest_index.todos:
        status_fragments.append(f"{len(latest_index.todos)} TODOs")

    index_summary = {
        "detected_stack": _detect_stack(latest_index, project),
        "manifest_paths": manifest_paths,
        "test_commands": test_commands,
        "build_commands": build_commands,
        "route_hints": route_hints,
        "deploy_hints": deploy_hints,
        "todo_count": len(latest_index.todos) if latest_index else 0,
        "todo_samples": (latest_index.todos[:5] if latest_index else []),
        "dependency_risks": dependency_risks,
        "file_count": len(latest_index.file_inventory) if latest_index else 0,
        "route_hint_count": len(route_hints),
        "manifest_count": len(manifest_paths),
    }
    actionable_metadata = _build_actionable_metadata(
        project,
        latest_index,
        test_commands=test_commands,
        build_commands=build_commands,
        route_hints=route_hints,
        deploy_hints=deploy_hints,
        dependency_risks=dependency_risks,
        freshness=freshness,
    )
    index_summary["actionable_metadata"] = actionable_metadata

    health_summary = {
        "status": project.health_status,
        "summary": "; ".join(status_fragments),
        "index_freshness": freshness,
        "missing_info": missing_info,
        "dependency_risks": dependency_risks,
        "actionable_metadata": actionable_metadata,
        "signals": [
            *([f"stack:{item}" for item in (project.detected_stack or [])[:4]]),
            *([f"deploy:{item}" for item in deploy_hints[:2]]),
            *([f"route:{item.split(':', 1)[0]}" for item in route_hints[:2]]),
            *([f"risk:{item}" for item in dependency_risks[:3]]),
            *([f"next:{item}" for item in actionable_metadata["next_action_hints"][:2]]),
        ],
    }

    return {"index_summary": index_summary, "health_summary": health_summary}


def _worker_command_example(item: WorkItem) -> str | None:
    payload = item.payload or {}
    command = payload.get("command")
    if command:
        return str(command)
    if (payload.get("engine") or "opencode") in {"opencode", "opencode-server"} and _work_item_prompt(item):
        return "opencode run --dangerously-skip-permissions <copy prompt from job payload>"
    return None


def _debug_prompt(item: WorkItem) -> str:
    payload = item.payload or {}
    result = item.result or {}
    prompt = _work_item_prompt(item)
    lines = [
        "Debug this failed Idea Refinery local-worker job in OpenCode.",
        f"Job ID: {item.id}",
        f"Job type: {item.job_type}",
        f"Status: {item.status}",
        f"Branch: {item.branch_name or payload.get('branch') or payload.get('branch_name') or 'unknown'}",
        f"Engine: {result.get('engine') or payload.get('engine') or 'opencode'}",
        f"Model: {result.get('model') or payload.get('model') or payload.get('role_model') or 'unspecified'}",
        f"Agent: {result.get('agent_name') or payload.get('agent') or payload.get('role') or 'unspecified'}",
        f"Error: {item.error or 'unknown'}",
    ]
    if item.logs:
        lines.extend(["", "Recent logs:", item.logs[-2000:]])
    if prompt:
        lines.extend(["", "Original prompt preview:", prompt[:2000]])
    lines.extend(["", "Please identify the likely root cause, the safest next command to run, and the smallest fix."])
    return "\n".join(lines)


class ProjectTwinService:
    def __init__(self, sqs_publisher: WorkerSqsPublisher | None = None) -> None:
        self.sqs_publisher = sqs_publisher or WorkerSqsPublisher()

    async def import_github_project(self, data: dict[str, Any]) -> dict[str, Any]:
        repo = get_repository()
        owner = (data.get("owner") or "").strip()
        repo_name = (data.get("repo") or data.get("repo_name") or "").strip()
        full_name = (data.get("repo_full_name") or f"{owner}/{repo_name}").strip("/")
        if "/" in full_name and (not owner or not repo_name):
            owner, repo_name = full_name.split("/", 1)
        if not owner or not repo_name:
            raise ValueError("owner and repo are required")

        installation_id = str(data.get("installation_id") or "")
        if not installation_id:
            raise ValueError("installation_id is required for GitHub App backed imports")

        await repo.save_github_installation(
            GitHubInstallation(
                installation_id=installation_id,
                account_login=owner,
                account_type=data.get("account_type") or "User",
            )
        )

        title = data.get("title") or full_name
        description = data.get("description") or (
            f"Existing GitHub project imported from {full_name}. "
            f"Current status: {data.get('current_status') or 'not yet assessed'}."
        )
        idea = Idea(
            title=title,
            slug=self._slug(title),
            description=description,
            current_phase=data.get("current_phase") or "build",
            source_type="github_project",
        )
        await repo.create_idea(idea)

        project = ProjectTwin(
            idea_id=idea.id,
            provider="github",
            installation_id=installation_id,
            owner=owner,
            repo=repo_name,
            repo_full_name=full_name,
            repo_url=data.get("repo_url") or f"https://github.com/{full_name}",
            clone_url=data.get("clone_url") or f"https://github.com/{full_name}.git",
            default_branch=data.get("default_branch") or "main",
            active_branch=data.get("active_branch"),
            deploy_url=data.get("deploy_url"),
            desired_outcome=data.get("desired_outcome"),
            current_status=data.get("current_status"),
        )
        await repo.save_project_twin(project)

        job = await self.enqueue_job(
            idea_id=idea.id,
            project_id=project.id,
            job_type="repo_index",
            payload={"reason": "initial_import", "default_branch": project.default_branch},
            idempotency_key=f"repo_index:{project.id}:initial",
        )
        return {"idea": to_jsonable(idea), "project": to_jsonable(project), "job": job_to_jsonable(job)}

    async def get_project_status(self, idea_id: str) -> dict[str, Any]:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        project = await repo.get_project_twin(idea_id)
        if not idea or not project:
            raise ValueError("Project twin not found")
        latest_index = await repo.get_latest_code_index(idea_id)
        jobs = await repo.list_work_items(idea_id)
        runs = await repo.list_agent_runs(idea_id)
        commits = await repo.list_project_commits(idea_id)
        summary = summarize_project_twin(project, latest_index, commits)
        factory_runs = []
        for run in (await repo.list_factory_runs(idea_id=idea_id))[:5]:
            bundle = await collect_factory_run_bundle(repo, run.id)
            if bundle:
                factory_runs.append({
                    "factory_run": to_jsonable(bundle["factory_run"]),
                    "tracking_manifest": to_jsonable(bundle["tracking_manifest"]),
                    "tracking_summary": bundle["tracking_summary"],
                    "phases": [to_jsonable(phase) for phase in bundle["phases"]],
                })
        return {
            "idea": to_jsonable(idea),
            "project": to_jsonable(project),
            "latest_index": to_jsonable(latest_index) if latest_index else None,
            "index_summary": summary["index_summary"],
            "health_summary": summary["health_summary"],
            "jobs": [job_to_jsonable(job) for job in jobs],
            "agent_runs": [to_jsonable(run) for run in runs[:10]],
            "commits": [to_jsonable(commit) for commit in commits[:10]],
            "factory_runs": factory_runs,
        }

    async def enqueue_reindex(self, idea_id: str) -> WorkItem:
        project = await get_repository().get_project_twin(idea_id)
        if not project:
            raise ValueError("Project twin not found")
        project.index_status = "queued"
        await get_repository().save_project_twin(project)
        return await self.enqueue_job(
            idea_id=idea_id,
            project_id=project.id,
            job_type="repo_index",
            payload={"reason": "manual_reindex", "default_branch": project.default_branch},
            idempotency_key=f"repo_index:{project.id}:{int(utcnow().timestamp())}",
        )

    async def enqueue_job(
        self,
        idea_id: str,
        project_id: str,
        job_type: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        priority: int = 50,
        factory_run_id: str | None = None,
        parent_work_item_id: str | None = None,
        rationale: str | None = None,
        correlation_id: str | None = None,
        dedupe_hash: str | None = None,
        budget: dict[str, Any] | None = None,
        stop_conditions: list[str] | None = None,
        branch_name: str | None = None,
        ledger_path: str | None = None,
        ledger_policy: str = "none",
    ) -> WorkItem:
        repo = get_repository()
        ledger_metadata = validate_ledger_metadata(
            ledger_path=ledger_path,
            ledger_policy=ledger_policy,
        )
        payload_data = _normalize_job_payload(payload)
        payload_data.setdefault("engine", "opencode")
        effective_factory_run_id = factory_run_id or payload_data.get("factory_run_id")
        payload_data["factory_run_id"] = effective_factory_run_id
        payload_data["ledger_policy"] = ledger_metadata["ledger_policy"]
        payload_data["ledger_path"] = ledger_metadata["ledger_path"]
        payload_data["ledger_context"] = extract_compact_ledger_context(ledger_metadata["ledger_path"])
        item = WorkItem(
            idea_id=idea_id,
            project_id=project_id,
            job_type=job_type,
            payload=payload_data,
            idempotency_key=idempotency_key,
            priority=priority,
            timeout_seconds=settings.worker_claim_timeout_seconds,
            factory_run_id=effective_factory_run_id,
            parent_work_item_id=parent_work_item_id,
            rationale=rationale,
            correlation_id=correlation_id,
            dedupe_hash=dedupe_hash,
            budget=dict(budget or {}),
            stop_conditions=list(stop_conditions or []),
            branch_name=branch_name,
            ledger_path=ledger_metadata["ledger_path"],
            ledger_policy=ledger_metadata["ledger_policy"],
        )
        await self._mark_duplicate_work(item, repo=repo)
        await repo.save_work_item(item)
        project = await repo.get_project_twin_by_id(project_id)
        if project:
            await self.sqs_publisher.send_job_available(item, project)
        return item

    async def list_jobs(self, idea_id: str | None = None) -> list[dict[str, Any]]:
        await self.requeue_expired_claims()
        return [job_to_jsonable(item) for item in await get_repository().list_work_items(idea_id)]

    async def claim_job(self, worker_id: str, capabilities: list[str] | None = None) -> dict[str, Any] | None:
        repo = get_repository()
        await self.requeue_expired_claims()
        running_projects = {
            item.project_id for item in await repo.list_work_items(statuses={"claimed", "running"})
        }
        for item in await repo.list_work_items(statuses=CLAIMABLE_STATUSES):
            if item.project_id in running_projects:
                continue
            if capabilities and item.job_type not in capabilities:
                continue
            normalized_payload = _normalize_job_payload(item.payload)
            if normalized_payload != (item.payload or {}):
                item.payload = normalized_payload
                await repo.save_work_item(item)
            project = await repo.get_project_twin_by_id(item.project_id)
            if not project:
                item.status = "failed_terminal"
                item.error = "Project twin not found"
                await repo.save_work_item(item)
                continue
            if capabilities:
                autonomy_level = (item.payload or {}).get("autonomy_level", "")
                from backend.app.services.autonomy import validate_worker_capabilities_for_autonomy
                missing = validate_worker_capabilities_for_autonomy(
                    capabilities, autonomy_level, worker_name=worker_id
                )
                if missing:
                    item.status = "failed_terminal"
                    item.error = (
                        f"Worker '{worker_id}' missing required capabilities for "
                        f"autonomy level '{autonomy_level}': {', '.join(missing)}. "
                        f"High-autonomy Factory Runs require opencode-server engine."
                    )
                    await repo.save_work_item(item)
                    continue
            item.status = "claimed"
            item.worker_id = worker_id
            item.claim_token = str(uuid.uuid4())
            item.claimed_at = utcnow()
            item.heartbeat_at = item.claimed_at
            worker = await repo.get_local_worker(worker_id)
            if worker and worker.engine:
                item.payload = {**(item.payload or {}), "engine": worker.engine}
            await repo.save_work_item(item)
            await self._upsert_agent_run(item, engine=(worker.engine if worker else None) or (item.payload or {}).get("engine") or "opencode", status="running")
            await self._refresh_factory_tracking(item)
            return {"job": job_to_jsonable(item, include_claim_token=True), "project": to_jsonable(project)}
        return None

    async def heartbeat_job(self, job_id: str, claim_token: str, worker_id: str, logs: str = "") -> dict[str, Any]:
        item = await self._locked_job(job_id, claim_token, worker_id)
        item.status = "running"
        item.heartbeat_at = utcnow()
        if logs:
            item.logs = self._append_log(item.logs, logs)
        await get_repository().save_work_item(item)
        await self._refresh_factory_tracking(item)
        return job_to_jsonable(item)

    async def complete_job(self, job_id: str, claim_token: str, worker_id: str, result: dict[str, Any] | None = None, logs: str = "") -> dict[str, Any]:
        repo = get_repository()
        item = await self._locked_job(job_id, claim_token, worker_id)
        result = dict(result or {})
        payload = item.payload or {}
        factory_run_id = payload.get("factory_run_id")
        ledger_sections_updated = result.get("ledger_sections_updated") or []
        if result.get("ledger_updated"):
            result["ledger_updated"] = True
            result["ledger_sections_updated"] = list(ledger_sections_updated)
        if item.ledger_policy in {"required", "strict"} and not result.get("ledger_updated"):
            warning = (
                "factory run ledger must be updated before completion. "
                "Set ledger_updated=true and ledger_sections_updated in the result."
            )
            result["ledger_validation_warnings"] = list(result.get("ledger_validation_warnings") or []) + [warning]
            if item.ledger_policy == "strict":
                item.status = "failed_terminal"
                item.error = warning
                item.result = result
                item.logs = self._append_log(item.logs, logs or f"[WARNING] {warning}")
                item.heartbeat_at = utcnow()
                await repo.save_work_item(item)
                await self._finalize_agent_run(item, status="failed", output=item.logs, result={"error": warning})
                await self._refresh_factory_tracking(item)
                return job_to_jsonable(item)
            item.logs = self._append_log(item.logs, f"[WARNING] {warning}")
        verification_commands = _verification_commands_for_payload(payload)
        graphify_required = any("graphify update" in command for command in verification_commands)
        graphify_updated = bool(result.get("graphify_updated"))
        verification_failure = _verification_failure_reason(payload=payload, result=result, job_type=item.job_type)
        high_autonomy = (payload.get("autonomy_level") or "") in HIGH_AUTONOMY_LEVELS
        graphify_issue = graphify_required and not graphify_updated
        if item.job_type != "repo_index" and graphify_issue:
            if high_autonomy:
                graphify_error = (
                    "graphify update . was required but graphify_updated is false."
                )
                verification_failure = f"{verification_failure} {graphify_error}".strip() if verification_failure else graphify_error
            else:
                logs_combined = f"{logs}\n" if logs else ""
                logs_combined += (
                    "[WARNING] graphify update . must be run before completion to keep the "
                    "knowledge graph current. Set graphify_updated=true in the result."
                )
                item.logs = self._append_log(item.logs, logs_combined)
        if item.job_type != "repo_index" and high_autonomy and verification_failure:
            item.status = "failed_terminal"
            item.error = verification_failure
            item.result = result
            item.heartbeat_at = utcnow()
            if logs:
                item.logs = self._append_log(item.logs, f"[ERROR] {verification_failure}\n{logs}")
            else:
                item.logs = self._append_log(item.logs, f"[ERROR] {verification_failure}")
            if result.get("branch_name") and not item.branch_name:
                item.branch_name = result["branch_name"]
            result.setdefault("branch_name", item.branch_name or payload.get("branch") or payload.get("branch_name"))
            draft_pr = _draft_pr_metadata_from_sources(payload, result)
            if draft_pr and "draft_pr" not in result:
                result["draft_pr"] = draft_pr
            result["token_economy"] = normalize_token_economy(
                result.get("token_economy"),
                work_item=item,
                payload=payload,
                result=result,
            )
            await repo.save_work_item(item)
            await self._finalize_agent_run(item, status="failed", output=item.logs, result={"error": verification_failure})
            await self._refresh_factory_tracking(item)
            return job_to_jsonable(item)
        result["token_economy"] = normalize_token_economy(
            result.get("token_economy"),
            work_item=item,
            payload=payload,
            result=result,
        )
        project = await repo.get_project_twin_by_id(item.project_id)
        draft_pr = _draft_pr_metadata_from_sources(payload, result)
        if (
            project
            and project.installation_id
            and project.owner
            and project.repo
            and project.default_branch
            and _should_create_draft_pull_request(item, payload, result, draft_pr)
        ):
            try:
                draft_pr = await _create_draft_pull_request(item=item, project=project, result=result, logs=logs)
                result["draft_pr"] = draft_pr
            except Exception as exc:
                message = str(exc).strip() or "unknown error"
                error = message if message.startswith("Draft pull request creation failed") else f"Draft pull request creation failed: {message}"
                item.status = "failed_terminal"
                item.error = error
                item.result = result
                item.heartbeat_at = utcnow()
                if logs:
                    item.logs = self._append_log(item.logs, f"[ERROR] {error}\n{logs}")
                else:
                    item.logs = self._append_log(item.logs, f"[ERROR] {error}")
                if result.get("branch_name") and not item.branch_name:
                    item.branch_name = result["branch_name"]
                result.setdefault("branch_name", item.branch_name or payload.get("branch") or payload.get("branch_name"))
                if draft_pr and "draft_pr" not in result:
                    result["draft_pr"] = draft_pr
                result["token_economy"] = normalize_token_economy(
                    result.get("token_economy"),
                    work_item=item,
                    payload=payload,
                    result=result,
                )
                await repo.save_work_item(item)
                await self._finalize_agent_run(item, status="failed", output=item.logs, result={"error": error})
                await self._refresh_factory_tracking(item)
                return job_to_jsonable(item)
        item.status = "completed"
        item.result = result
        item.heartbeat_at = utcnow()
        if result.get("engine") or payload.get("engine"):
            result.setdefault("engine", result.get("engine") or payload.get("engine"))
        if result.get("model") or payload.get("model"):
            result.setdefault("model", result.get("model") or payload.get("model"))
        if result.get("agent_name") or payload.get("agent") or payload.get("agent_name"):
            result.setdefault("agent_name", result.get("agent_name") or payload.get("agent") or payload.get("agent_name"))
        if result.get("branch_name"):
            item.branch_name = result["branch_name"]
        if item.branch_name and not result.get("branch_name"):
            result["branch_name"] = item.branch_name
        draft_pr = _draft_pr_metadata_from_sources(payload, result)
        if draft_pr and "draft_pr" not in result:
            result["draft_pr"] = draft_pr
        if logs:
            item.logs = self._append_log(item.logs, logs)
        await repo.save_work_item(item)
        await self._finalize_agent_run(item, status="completed", output=logs or result.get("agent_output") or "", result=result)

        if item.status == "completed" and result.get("commit_sha") and result.get("branch_name"):
            await repo.add_project_commit(
                ProjectCommit(
                    idea_id=item.idea_id,
                    project_id=item.project_id,
                    work_item_id=item.id,
                    branch_name=result["branch_name"],
                    commit_sha=result["commit_sha"],
                    message=result.get("commit_message") or f"Idea Refinery job {item.id}",
                    author=result.get("author"),
                )
            )

        if project:
            if item.status == "completed":
                project.health_status = "healthy" if result.get("tests_passed", item.job_type == "repo_index") else project.health_status
            if item.job_type == "repo_index" and item.status == "completed":
                await self._store_code_index(project, item, result)
            latest_index = await repo.get_latest_code_index(project.idea_id)
            commits = await repo.list_project_commits(project.idea_id)
            summary = summarize_project_twin(project, latest_index, commits)
            project.health_status = self._derive_project_health(summary["health_summary"])
            await repo.save_project_twin(project)
        await self._refresh_factory_tracking(item)
        return job_to_jsonable(item)

    async def fail_job(self, job_id: str, claim_token: str, worker_id: str, error: str, retryable: bool = True, logs: str = "") -> dict[str, Any]:
        item = await self._locked_job(job_id, claim_token, worker_id)
        item.retry_count += 1
        item.error = error
        if logs:
            item.logs = self._append_log(item.logs, logs)
        if retryable and item.retry_count <= settings.worker_max_retries:
            item.status = "failed_retryable"
            item.run_after = utcnow() + timedelta(minutes=min(30, item.retry_count * 2))
        else:
            item.status = "failed_terminal"
        await get_repository().save_work_item(item)
        await self._finalize_agent_run(item, status="failed", output=logs, result={"error": error, "retryable": retryable})
        await self._refresh_factory_tracking(item)
        return job_to_jsonable(item)

    async def requeue_expired_claims(self) -> None:
        repo = get_repository()
        now = utcnow()
        for item in await repo.list_work_items(statuses={"claimed", "running"}):
            heartbeat = item.heartbeat_at or item.claimed_at or item.updated_at
            if heartbeat and (now - heartbeat).total_seconds() > item.timeout_seconds:
                item.status = "waiting_for_machine"
                item.worker_id = None
                item.claim_token = None
                item.error = "Worker heartbeat expired"
                await repo.save_work_item(item)
                await self._finalize_agent_run(item, status="timed_out", output=item.logs, result={"error": item.error})
                await self._refresh_factory_tracking(item)

    async def _locked_job(self, job_id: str, claim_token: str, worker_id: str) -> WorkItem:
        repo = get_repository()
        worker = await repo.get_local_worker(worker_id)
        if worker and worker.status != "approved":
            raise ValueError("Worker is not approved")
        item = await repo.get_work_item(job_id)
        if not item:
            raise ValueError("Job not found")
        if item.claim_token != claim_token or item.worker_id != worker_id:
            raise ValueError("Job claim does not belong to this worker")
        if item.status in TERMINAL_STATUSES:
            raise ValueError(f"Job is already terminal: {item.status}")
        return item

    async def _store_code_index(self, project: ProjectTwin, item: WorkItem, result: dict[str, Any]) -> None:
        index = result.get("code_index") or {}
        commit_sha = result.get("commit_sha") or index.get("commit_sha") or project.last_indexed_commit or "unknown"
        route_map = index.get("route_map") or []
        manifests = index.get("manifests") or []
        draft_artifact = CodeIndexArtifact(
            project_id=project.id,
            idea_id=project.idea_id,
            commit_sha=commit_sha,
            file_inventory=index.get("file_inventory") or [],
            manifests=manifests,
            dependency_graph=index.get("dependency_graph") or {},
            route_map=route_map,
            test_commands=index.get("test_commands") or [],
            architecture_summary=index.get("architecture_summary") or "",
            risks=index.get("risks") or [],
            todos=index.get("todos") or [],
            searchable_chunks=index.get("searchable_chunks") or [],
        )
        test_commands, _build_commands = _detect_commands(draft_artifact)
        draft_artifact.test_commands = test_commands
        dependency_risks = _detect_dependency_risks(draft_artifact)
        artifact = CodeIndexArtifact(
            project_id=project.id,
            idea_id=project.idea_id,
            commit_sha=commit_sha,
            file_inventory=draft_artifact.file_inventory,
            manifests=manifests,
            dependency_graph=draft_artifact.dependency_graph,
            route_map=route_map,
            test_commands=test_commands,
            architecture_summary=draft_artifact.architecture_summary,
            risks=list(dict.fromkeys(draft_artifact.risks + dependency_risks)),
            todos=draft_artifact.todos,
            searchable_chunks=draft_artifact.searchable_chunks,
        )
        await get_repository().put_code_index(artifact)
        project.last_indexed_commit = commit_sha
        project.detected_stack = index.get("detected_stack") or _detect_stack(artifact, project)
        project.test_commands = artifact.test_commands or project.test_commands
        project.index_status = "indexed"
        if artifact.architecture_summary:
            await get_repository().put_report(
                Report(
                    idea_id=project.idea_id,
                    phase="tech_spec",
                    title="Codebase Dossier",
                    content=artifact.architecture_summary,
                    content_path=f"CODE_INDEX#{artifact.id}",
                )
            )

    def _derive_project_health(self, health_summary: dict[str, Any]) -> str:
        freshness = health_summary.get("index_freshness", {}) if isinstance(health_summary, dict) else {}
        if freshness.get("state") == "stale":
            return "needs_reindex"
        if health_summary.get("dependency_risks"):
            return "needs_attention"
        return "healthy"

    def _slug(self, title: str) -> str:
        return re.sub(r"[^\w-]", "", title.lower().replace(" ", "-")) or "idea"

    def _append_log(self, current: str, new: str) -> str:
        text = f"{current.rstrip()}\n{new.strip()}".strip()
        return text[-20000:]

    async def _refresh_factory_tracking(self, item: WorkItem) -> None:
        payload = item.payload or {}
        factory_run_id = payload.get("factory_run_id")
        if not factory_run_id:
            return
        await refresh_factory_run_tracking_manifest(get_repository(), factory_run_id)

    async def _upsert_agent_run(self, item: WorkItem, *, engine: str, status: str, command: str | None = None) -> AgentRun:
        repo = get_repository()
        existing = await repo.list_agent_runs(item.idea_id)
        run = next((entry for entry in existing if entry.work_item_id == item.id), None)
        payload = item.payload or {}
        branch_name = item.branch_name or payload.get("branch") or payload.get("branch_name")
        agent_run = run or AgentRun(
            work_item_id=item.id,
            idea_id=item.idea_id,
            project_id=item.project_id,
            engine=engine,
            agent_name=payload.get("agent") or payload.get("agent_name") or payload.get("role"),
            model=payload.get("model") or payload.get("role_model"),
            command=command or _worker_command_example(item),
            status=status,
            prompt=str(payload.get("prompt") or payload.get("role_prompt") or payload.get("goal") or ""),
            output=item.logs or "",
            branch_name=branch_name,
        )
        agent_run.engine = engine or agent_run.engine
        agent_run.agent_name = payload.get("agent") or payload.get("agent_name") or payload.get("role") or agent_run.agent_name
        agent_run.model = payload.get("model") or payload.get("role_model") or agent_run.model
        agent_run.command = command or agent_run.command
        agent_run.prompt = agent_run.prompt or _work_item_prompt(item)
        agent_run.branch_name = branch_name or agent_run.branch_name
        agent_run.status = status
        await repo.save_agent_run(agent_run)
        item.agent_run_id = agent_run.id
        await repo.save_work_item(item)
        return agent_run

    async def _finalize_agent_run(self, item: WorkItem, *, status: str, output: str, result: dict[str, Any]) -> None:
        repo = get_repository()
        run_id = item.agent_run_id
        if not run_id:
            await self._upsert_agent_run(item, engine=result.get("engine") or (item.payload or {}).get("engine") or "opencode", status=status)
            run_id = item.agent_run_id
        if not run_id:
            return
        run = None
        for entry in await repo.list_agent_runs(item.idea_id):
            if entry.id == run_id:
                run = entry
                break
        if not run:
            return
        run.status = status
        run.output = output or result.get("agent_output") or run.output
        run.agent_name = result.get("agent_name") or result.get("agent") or run.agent_name
        run.model = result.get("model") or run.model
        run.command = result.get("command") or run.command
        run.branch_name = result.get("branch_name") or item.branch_name or run.branch_name
        run.completed_at = utcnow()
        await repo.save_agent_run(run)

    async def _mark_duplicate_work(self, item: WorkItem, *, repo: Any) -> None:
        payload = dict(item.payload or {})
        candidate_keys = [key for key in (payload.get("duplicate_work_key"), item.idempotency_key, item.dedupe_hash) if key]
        if not candidate_keys:
            item.payload = payload
            return

        existing_items = await repo.list_work_items(
            idea_id=item.idea_id,
            statuses=DUPLICATE_WORK_MATCH_STATUSES,
        )
        for existing in existing_items:
            if existing.id == item.id or existing.project_id != item.project_id:
                continue
            if _duplicate_work_keys(existing) & set(candidate_keys):
                payload["duplicate_work_detected"] = True
                payload.setdefault("duplicate_work_key", next(
                    key for key in candidate_keys if key in _duplicate_work_keys(existing)
                ))
                item.payload = payload
                return

        item.payload = payload
