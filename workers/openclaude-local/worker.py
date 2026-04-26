from __future__ import annotations

import argparse
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CAPABILITIES = [
    "repo_index",
    "architecture_dossier",
    "gap_analysis",
    "build_task_plan",
    "agent_branch_work",
    "test_verify",
    "sync_remote_state",
]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".svelte-kit"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".svelte", ".go", ".rs", ".java", ".cs", ".php", ".rb"}
MANIFEST_NAMES = {"package.json", "pyproject.toml", "requirements.txt", "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "Cargo.toml", "go.mod", "Dockerfile"}


@dataclass
class WorkerConfig:
    api_base: str
    display_name: str = "OpenClaude local worker"
    engine: str = "openclaude"
    allow_full_control: bool = False
    workspace_root: str = "~/.idearefinery-worker/repos"
    poll_seconds: int = 20
    capabilities: list[str] = field(default_factory=lambda: DEFAULT_CAPABILITIES.copy())
    openclaude: dict[str, Any] = field(default_factory=dict)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


class ApiClient:
    def __init__(self, api_base: str, token: str = "") -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token

    def get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(f"{self.api_base}{path}", headers=self._headers(), method="GET")
        return self._send(request)

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(f"{self.api_base}{path}", data=data, headers=self._headers(), method="POST")
        return self._send(request)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _send(self, request: urllib.request.Request) -> dict[str, Any]:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8") or "{}")


class SqsTransport:
    def __init__(self, state: dict[str, Any], sqs_client: Any | None = None) -> None:
        self.state = state
        self.credentials = state.get("credentials") or {}
        self.client = sqs_client

    def configured(self) -> bool:
        return bool(self.credentials.get("command_queue_url"))

    def receive(self) -> list[dict[str, Any]]:
        if not self.configured():
            return []
        client = self.client or self._client()
        response = client.receive_message(
            QueueUrl=self.credentials["command_queue_url"],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=1800,
        )
        return response.get("Messages", [])

    def delete(self, message: dict[str, Any]) -> None:
        if not self.configured():
            return
        (self.client or self._client()).delete_message(
            QueueUrl=self.credentials["command_queue_url"],
            ReceiptHandle=message["ReceiptHandle"],
        )

    def send_event(self, worker_id: str, event_type: str, payload: dict[str, Any]) -> None:
        if not self.credentials.get("event_queue_url"):
            return
        body = {"worker_id": worker_id, "type": event_type, "payload": payload}
        (self.client or self._client()).send_message(
            QueueUrl=self.credentials["event_queue_url"],
            MessageBody=json.dumps(body),
            MessageGroupId=f"worker:{worker_id}",
            MessageDeduplicationId=f"{worker_id}:{event_type}:{payload.get('work_item_id', '')}:{int(time.time() * 1000)}",
        )

    def _client(self):
        import boto3

        return boto3.client(
            "sqs",
            region_name=self.credentials.get("region"),
            aws_access_key_id=self.credentials.get("access_key_id"),
            aws_secret_access_key=self.credentials.get("secret_access_key"),
            aws_session_token=self.credentials.get("session_token"),
        )


class OpenClaudeAdapter:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings

    def command(self, prompt: str) -> list[str]:
        command = ["openclaude", "-p"]
        if self.settings.get("agent"):
            command += ["--agent", self.settings["agent"]]
        if self.settings.get("model"):
            command += ["--model", self.settings["model"]]
        if self.settings.get("permission_mode"):
            command += ["--permission-mode", self.settings["permission_mode"]]
        if self.settings.get("output_format"):
            command += ["--output-format", self.settings["output_format"]]
        if self.settings.get("max_budget_usd"):
            command += ["--max-budget-usd", str(self.settings["max_budget_usd"])]
        if self.settings.get("system_prompt"):
            command += ["--system-prompt", self.settings["system_prompt"]]
        for directory in self.settings.get("additional_dirs") or []:
            command += ["--add-dir", directory]
        command.append(prompt)
        return command


class LocalWorker:
    def __init__(self, config: WorkerConfig, state_store: StateStore, state: dict[str, Any], sqs_client: Any | None = None) -> None:
        self.config = config
        self.state_store = state_store
        self.state = state
        self.api = ApiClient(config.api_base, self.state.get("api_token", ""))
        self.sqs = SqsTransport(state, sqs_client=sqs_client)
        self.workspace_root = Path(config.workspace_root).expanduser()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def run_once(self) -> bool:
        for message in self.sqs.receive():
            envelope = json.loads(message.get("Body") or "{}")
            if self.handle_envelope(envelope):
                self.sqs.delete(message)
                return True
        return self.claim_and_process()

    def handle_envelope(self, envelope: dict[str, Any]) -> bool:
        if envelope.get("type") != "job_available":
            return False
        if envelope.get("job_type") not in self.config.capabilities:
            return False
        return self.claim_and_process()

    def claim_and_process(self) -> bool:
        claim = self.api.post("/api/worker/claim", {"worker_id": self.state["worker_id"], "capabilities": self.config.capabilities}).get("claim")
        if not claim:
            return False
        job = claim["job"]
        project = claim["project"]
        logs: list[str] = []
        try:
            self._submit_update("heartbeat", job, {"logs": "Claimed job."})
            result = self.process_job(job, project, logs)
            self._submit_update("job_completed", job, {"result": result, "logs": "\n".join(logs)})
        except Exception as exc:
            self._submit_update("job_failed", job, {"error": f"{type(exc).__name__}: {exc}", "retryable": True, "logs": "\n".join(logs)})
        return True

    def process_job(self, job: dict[str, Any], project: dict[str, Any], logs: list[str]) -> dict[str, Any]:
        repo_dir = self.workspace_root / self._slug(project["repo_full_name"])
        self._ensure_repo(repo_dir, project["clone_url"], project.get("default_branch") or "main", logs)
        job_type = job["job_type"]
        if job_type == "repo_index":
            index = self._index_repo(repo_dir)
            return {"commit_sha": self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip(), "code_index": index, "tests_passed": True}
        if job_type in {"architecture_dossier", "gap_analysis", "build_task_plan"}:
            index = self._index_repo(repo_dir)
            prompt = "Analyze this repository index and return a concise implementation-ready dossier.\n\n" + json.dumps(index)[:30000]
            index["architecture_summary"] = self._run_agent(repo_dir, prompt, logs)
            return {"commit_sha": self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip(), "code_index": index, "tests_passed": True}
        if job_type in {"agent_branch_work", "test_verify"}:
            return self._branch_work(repo_dir, job, project, logs)
        if job_type == "sync_remote_state":
            self._git(repo_dir, ["fetch", "--all", "--prune"], logs)
            return {"commit_sha": self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip(), "tests_passed": True}
        raise ValueError(f"Unsupported job type: {job_type}")

    def _branch_work(self, repo_dir: Path, job: dict[str, Any], project: dict[str, Any], logs: list[str]) -> dict[str, Any]:
        payload = job.get("payload") or {}
        full_control = self.config.allow_full_control and bool(payload.get("allow_full_control"))
        branch = payload.get("branch_name") or f"idearefinery/{self._slug(project['repo_full_name'])}/{job['id'][:8]}"
        self._git(repo_dir, ["checkout", "-B", branch], logs)
        prompt = payload.get("prompt") or "Implement the queued IdeaRefinery coding task, keep changes scoped, and run tests."
        if not full_control:
            prompt += "\n\nAutonomy boundary: create a branch and report results. Do not merge to main or force-push protected branches."
        output = self._run_agent(repo_dir, prompt, logs)
        tests_passed = self._run_tests(repo_dir, payload.get("test_commands") or [], logs)
        status = self._git(repo_dir, ["status", "--porcelain"], logs).strip()
        commit_sha = self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip()
        if status:
            self._git(repo_dir, ["add", "."], logs)
            message = payload.get("commit_message") or f"feat: idea refinery task {job['id'][:8]}"
            self._git(repo_dir, ["commit", "-m", message], logs)
            commit_sha = self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip()
            self._git(repo_dir, ["push", "-u", "origin", branch], logs)
        return {"branch_name": branch, "commit_sha": commit_sha, "commit_message": payload.get("commit_message") or f"IdeaRefinery task {job['id'][:8]}", "agent_output": output, "tests_passed": tests_passed, "full_control_used": full_control}

    def _ensure_repo(self, repo_dir: Path, clone_url: str, branch: str, logs: list[str]) -> None:
        if repo_dir.exists():
            self._git(repo_dir, ["fetch", "--all", "--prune"], logs)
            self._git(repo_dir, ["checkout", branch], logs, check=False)
            self._git(repo_dir, ["pull", "--ff-only"], logs, check=False)
            return
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        self._run(["git", "clone", "--branch", branch, clone_url, str(repo_dir)], repo_dir.parent, logs)

    def _index_repo(self, repo_dir: Path) -> dict[str, Any]:
        inventory: list[dict[str, Any]] = []
        manifests: list[dict[str, str]] = []
        route_map: list[dict[str, str]] = []
        todos: list[str] = []
        for path in repo_dir.rglob("*"):
            if any(part in SKIP_DIRS for part in path.relative_to(repo_dir).parts) or not path.is_file():
                continue
            rel = path.relative_to(repo_dir).as_posix()
            inventory.append({"path": rel, "size": path.stat().st_size, "kind": self._kind(path)})
            if path.name in MANIFEST_NAMES:
                manifests.append({"path": rel, "content": self._read(path, 24000)})
            if path.suffix.lower() in SOURCE_SUFFIXES and path.stat().st_size < 250000:
                for line in self._read(path, 60000).splitlines():
                    if "TODO" in line or "FIXME" in line:
                        todos.append(f"{rel}: {line.strip()[:180]}")
                    if "@app." in line or "APIRouter" in line or "router." in line:
                        route_map.append({"path": rel, "line": line.strip()[:220]})
        return {"file_inventory": inventory, "manifests": manifests, "route_map": route_map[:200], "test_commands": self._detect_tests(manifests), "risks": [], "todos": todos[:200], "searchable_chunks": []}

    def _run_agent(self, repo_dir: Path, prompt: str, logs: list[str]) -> str:
        if self.config.engine == "openclaude" and shutil.which("openclaude"):
            return self._run(OpenClaudeAdapter(self.config.openclaude).command(prompt), repo_dir, logs, check=False)
        if self.config.engine == "opencode" and shutil.which("opencode"):
            return self._run(["opencode", "run", prompt], repo_dir, logs, check=False)
        if shutil.which("codex"):
            return self._run(["codex", "exec", "-C", str(repo_dir), prompt], repo_dir, logs, check=False)
        logs.append("No local coding engine found; returning deterministic fallback.")
        return ""

    def _run_tests(self, repo_dir: Path, commands: list[str], logs: list[str]) -> bool:
        if not commands:
            commands = self._detect_tests(self._index_repo(repo_dir).get("manifests") or [])
        ok = True
        for command in commands[:4]:
            result = self._run(command, repo_dir, logs, shell=True, check=False)
            ok = ok and "exit code: 0" in result
        return ok

    def _event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.sqs.send_event(self.state["worker_id"], event_type, payload)

    def _submit_update(self, event_type: str, job: dict[str, Any], payload: dict[str, Any]) -> None:
        event_payload = {"work_item_id": job["id"], "claim_token": job["claim_token"], **payload}
        if self.sqs.credentials.get("event_queue_url"):
            self._event(event_type, event_payload)
            return
        if event_type == "heartbeat":
            self.api.post(f"/api/worker/jobs/{job['id']}/heartbeat", {"worker_id": self.state["worker_id"], "claim_token": job["claim_token"], "logs": payload.get("logs", "")})
        elif event_type == "job_completed":
            self.api.post(f"/api/worker/jobs/{job['id']}/complete", {"worker_id": self.state["worker_id"], "claim_token": job["claim_token"], "result": payload.get("result") or {}, "logs": payload.get("logs", "")})
        elif event_type == "job_failed":
            self.api.post(f"/api/worker/jobs/{job['id']}/fail", {"worker_id": self.state["worker_id"], "claim_token": job["claim_token"], "error": payload.get("error") or "Worker failed", "retryable": bool(payload.get("retryable", True)), "logs": payload.get("logs", "")})

    def _git(self, repo_dir: Path, args: list[str], logs: list[str], check: bool = True) -> str:
        return self._run(["git", *args], repo_dir, logs, check=check)

    def _run(self, command: list[str] | str, cwd: Path, logs: list[str], shell: bool = False, check: bool = True) -> str:
        label = command if isinstance(command, str) else " ".join(command)
        logs.append(f"$ {label}")
        proc = subprocess.run(command, cwd=cwd, shell=shell, text=True, capture_output=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        if output.strip():
            logs.append(output.strip()[-8000:])
        logs.append(f"exit code: {proc.returncode}")
        if check and proc.returncode != 0:
            raise RuntimeError(f"Command failed: {label}")
        return output + f"\nexit code: {proc.returncode}"

    def _detect_tests(self, manifests: list[dict[str, str]]) -> list[str]:
        commands: list[str] = []
        for manifest in manifests:
            if manifest["path"].endswith("package.json"):
                try:
                    scripts = json.loads(manifest["content"]).get("scripts", {})
                    if "test" in scripts:
                        commands.append("npm test")
                    if "build" in scripts:
                        commands.append("npm run build")
                except json.JSONDecodeError:
                    pass
            if manifest["path"].endswith("pyproject.toml"):
                commands.append("python -m pytest")
        return commands

    def _kind(self, path: Path) -> str:
        if path.name in MANIFEST_NAMES:
            return "manifest"
        if path.suffix.lower() in SOURCE_SUFFIXES:
            return "source"
        if path.suffix.lower() in {".md", ".txt", ".rst"}:
            return "doc"
        return "asset"

    def _read(self, path: Path, limit: int) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
        except OSError:
            return ""

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "repo"


def load_config(path: Path | None, api_base: str | None = None) -> WorkerConfig:
    data: dict[str, Any] = {}
    if path and path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    env_api_base = api_base or os.getenv("IDEAREFINERY_API_BASE_URL")
    if env_api_base:
        data["api_base"] = env_api_base
    data.setdefault("api_base", "http://localhost:8000")
    data["engine"] = os.getenv("IDEAREFINERY_WORKER_ENGINE", data.get("engine", "openclaude"))
    data["workspace_root"] = os.getenv("IDEAREFINERY_WORKER_WORKSPACE", data.get("workspace_root", "~/.idearefinery-worker/repos"))
    data["allow_full_control"] = os.getenv("IDEAREFINERY_WORKER_ALLOW_FULL_CONTROL", str(data.get("allow_full_control", "false"))).lower() in {"1", "true", "yes"}
    return WorkerConfig(**data)


def pair(config: WorkerConfig, state_store: StateStore, tenant_id: str | None = None) -> dict[str, Any]:
    client = ApiClient(config.api_base)
    payload = {
        "display_name": config.display_name,
        "machine_name": platform.node() or os.environ.get("COMPUTERNAME", "local-worker"),
        "platform": f"{platform.system()} {platform.release()}",
        "engine": config.engine,
        "capabilities": config.capabilities,
        "config": {"autonomy": "branch_pr", "allow_full_control": config.allow_full_control, "openclaude": config.openclaude},
    }
    if tenant_id:
        payload["tenant_id"] = tenant_id
    registered = client.post("/api/local-workers/register", payload)
    request = registered["request"]
    pairing_token = registered["pairing_token"]
    print(f"Pairing request created: {request['id']}")
    while True:
        status = client.get(f"/api/local-workers/registrations/{request['id']}?pairing_token={pairing_token}")
        if status["request"]["status"] == "approved":
            credentials = status["credentials"]
            if not credentials.get("api_token"):
                raise RuntimeError("Approval succeeded but no API token was returned to this pairing session.")
            state = {"api_base": config.api_base, "worker_id": status["worker"]["id"], "api_token": credentials["api_token"], "credentials": credentials}
            state_store.save(state)
            print(f"Approved worker {state['worker_id']}.")
            return state
        if status["request"]["status"] == "denied":
            raise RuntimeError(f"Pairing denied: {status['request'].get('decision_reason') or 'no reason'}")
        print("Waiting for approval in the Local Workers page...")
        time.sleep(5)


def default_state_path() -> Path:
    return Path(os.getenv("IDEAREFINERY_WORKER_STATE", "~/.idearefinery-worker/openclaude-local/state.json")).expanduser()


def main() -> int:
    print("=" * 70)
    print("DEPRECATION WARNING")
    print("=" * 70)
    print("The Python CLI worker is deprecated. Use the Tauri worker app")
    print("(worker-app/) instead, which supports OpenCode server mode,")
    print("LiteLLM proxy, circuit breakers, and SQS checkpoint events.")
    print("=" * 70)
    print()
    parser = argparse.ArgumentParser(description="IdeaRefinery OpenClaude local worker")
    parser.add_argument("command", choices=["pair", "run", "once"])
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("worker-config.json"))
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--tenant-id", default=None)
    args = parser.parse_args()

    config = load_config(args.config if args.config.exists() else None, args.api_base)
    state_store = StateStore(args.state)
    if args.command == "pair":
        pair(config, state_store, args.tenant_id)
        return 0

    state = state_store.load()
    if not state.get("worker_id") or not state.get("api_token"):
        raise RuntimeError("Worker is not paired yet. Run: python worker.py pair --api-base <url>")
    worker = LocalWorker(config, state_store, state)
    while True:
        try:
            did_work = worker.run_once()
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"worker connection unavailable: {exc}", file=sys.stderr)
            did_work = False
        if args.command == "once":
            return 0
        time.sleep(5 if did_work else max(5, config.poll_seconds + random.randint(-3, 6)))


if __name__ == "__main__":
    raise SystemExit(main())
