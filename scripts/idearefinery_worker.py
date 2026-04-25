from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".svelte-kit"}
MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Dockerfile",
    "docker-compose.yml",
}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".svelte", ".go", ".rs", ".java", ".cs", ".php", ".rb"}


class WorkerClient:
    def __init__(self, api_base: str, token: str = "") -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.api_base}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        return self._send(request)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-IdeaRefinery-Worker-Token"] = self.token
        return headers

    def _send(self, request: urllib.request.Request) -> dict[str, Any]:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8") or "{}")


class IdeaRefineryWorker:
    def __init__(
        self,
        api_base: str,
        worker_id: str,
        token: str,
        workspace_root: Path,
        preferred_engine: str = "openclaude",
    ) -> None:
        self.client = WorkerClient(api_base, token)
        self.worker_id = worker_id
        self.workspace_root = workspace_root
        self.preferred_engine = preferred_engine
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def run_once(self) -> bool:
        claim = self.client.post(
            "/api/worker/claim",
            {
                "worker_id": self.worker_id,
                "capabilities": ["repo_index", "architecture_dossier", "gap_analysis", "build_task_plan", "agent_branch_work", "test_verify", "sync_remote_state"],
            },
        ).get("claim")
        if not claim:
            return False

        job = claim["job"]
        project = claim["project"]
        job_id = job["id"]
        claim_token = job["claim_token"]
        log_lines: list[str] = []
        try:
            self._heartbeat(job_id, claim_token, "Claimed job.")
            result = self.process_job(job, project, log_lines)
            self.client.post(
                f"/api/worker/jobs/{job_id}/complete",
                {
                    "worker_id": self.worker_id,
                    "claim_token": claim_token,
                    "result": result,
                    "logs": "\n".join(log_lines),
                },
            )
            return True
        except Exception as exc:
            log_lines.append(f"ERROR: {type(exc).__name__}: {exc}")
            self.client.post(
                f"/api/worker/jobs/{job_id}/fail",
                {
                    "worker_id": self.worker_id,
                    "claim_token": claim_token,
                    "error": f"{type(exc).__name__}: {exc}",
                    "retryable": True,
                    "logs": "\n".join(log_lines),
                },
            )
            return True

    def process_job(self, job: dict[str, Any], project: dict[str, Any], logs: list[str]) -> dict[str, Any]:
        repo_dir = self._repo_dir(project)
        clone_url = project["clone_url"]
        branch = project.get("default_branch") or "main"
        self._ensure_repo(repo_dir, clone_url, branch, logs)

        job_type = job["job_type"]
        if job_type == "repo_index":
            index = self._index_repo(repo_dir, logs)
            summary = self._architecture_summary(repo_dir, index, logs)
            index["architecture_summary"] = summary
            return {
                "commit_sha": self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip(),
                "code_index": index,
                "tests_passed": True,
            }
        if job_type in {"architecture_dossier", "gap_analysis", "build_task_plan"}:
            index = self._index_repo(repo_dir, logs)
            return {
                "commit_sha": self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip(),
                "code_index": {**index, "architecture_summary": self._architecture_summary(repo_dir, index, logs)},
                "tests_passed": True,
            }
        if job_type in {"agent_branch_work", "test_verify"}:
            return self._run_agent_branch_work(repo_dir, job, project, logs)
        if job_type == "sync_remote_state":
            self._git(repo_dir, ["fetch", "--all", "--prune"], logs)
            return {"commit_sha": self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip(), "tests_passed": True}
        raise ValueError(f"Unsupported job type: {job_type}")

    def _ensure_repo(self, repo_dir: Path, clone_url: str, branch: str, logs: list[str]) -> None:
        if repo_dir.exists():
            self._git(repo_dir, ["fetch", "--all", "--prune"], logs)
            self._git(repo_dir, ["checkout", branch], logs, check=False)
            self._git(repo_dir, ["pull", "--ff-only"], logs, check=False)
            return
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        self._run(["git", "clone", "--branch", branch, clone_url, str(repo_dir)], repo_dir.parent, logs)

    def _index_repo(self, repo_dir: Path, logs: list[str]) -> dict[str, Any]:
        file_inventory: list[dict[str, Any]] = []
        manifests: list[dict[str, Any]] = []
        todos: list[str] = []
        routes: list[dict[str, str]] = []
        chunks: list[dict[str, str]] = []
        detected_stack: set[str] = set()

        for path in self._walk(repo_dir):
            rel = path.relative_to(repo_dir).as_posix()
            size = path.stat().st_size
            suffix = path.suffix.lower()
            file_inventory.append({"path": rel, "size": size, "kind": self._kind(path)})
            if path.name in MANIFEST_NAMES:
                content = self._read_text(path, 24000)
                manifests.append({"path": rel, "content": content})
                detected_stack.update(self._detect_stack(path, content))
            if suffix in SOURCE_SUFFIXES and size <= 250000:
                content = self._read_text(path, 60000)
                for line in content.splitlines():
                    if "TODO" in line or "FIXME" in line:
                        todos.append(f"{rel}: {line.strip()[:180]}")
                    if "@app." in line or "APIRouter" in line or "router." in line or "Route::" in line:
                        routes.append({"path": rel, "line": line.strip()[:220]})
                if len(chunks) < 400:
                    chunks.append({"path": rel, "content": content[:6000]})

        test_commands = self._detect_test_commands(manifests)
        risks = self._detect_risks(repo_dir, manifests, file_inventory)
        return {
            "file_inventory": file_inventory,
            "manifests": manifests,
            "dependency_graph": {"manifests": [item["path"] for item in manifests]},
            "route_map": routes[:200],
            "test_commands": test_commands,
            "detected_stack": sorted(detected_stack),
            "risks": risks,
            "todos": todos[:200],
            "searchable_chunks": chunks,
        }

    def _architecture_summary(self, repo_dir: Path, index: dict[str, Any], logs: list[str]) -> str:
        prompt = (
            "Analyze this repository index for Idea Refinery. Return a concise markdown codebase dossier with: "
            "current architecture, what exists, missing production-readiness gaps, safest next build tasks, "
            "test commands, and risk notes.\n\n"
            + json.dumps({k: v for k, v in index.items() if k != "searchable_chunks"}, indent=2)[:30000]
        )
        output = self._run_agent(repo_dir, prompt, logs)
        if output.strip():
            return output.strip()
        return self._fallback_summary(index)

    def _run_agent_branch_work(self, repo_dir: Path, job: dict[str, Any], project: dict[str, Any], logs: list[str]) -> dict[str, Any]:
        branch = job.get("payload", {}).get("branch_name") or f"idearefinery/{self._slug(project['repo_full_name'])}/{job['id'][:8]}"
        self._git(repo_dir, ["checkout", "-B", branch], logs)
        prompt = job.get("payload", {}).get("prompt") or "Implement the queued Idea Refinery task, keep the change scoped, and run tests."
        output = self._run_agent(repo_dir, prompt, logs)
        tests_passed = self._run_tests(repo_dir, job.get("payload", {}).get("test_commands") or [], logs)
        status = self._git(repo_dir, ["status", "--porcelain"], logs).strip()
        commit_sha = self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip()
        if status:
            self._git(repo_dir, ["add", "."], logs)
            message = job.get("payload", {}).get("commit_message") or f"feat: idea refinery task {job['id'][:8]}"
            self._git(repo_dir, ["commit", "-m", message], logs)
            commit_sha = self._git(repo_dir, ["rev-parse", "HEAD"], logs).strip()
            self._git(repo_dir, ["push", "-u", "origin", branch], logs)
        return {
            "branch_name": branch,
            "commit_sha": commit_sha,
            "commit_message": job.get("payload", {}).get("commit_message") or f"Idea Refinery task {job['id'][:8]}",
            "agent_output": output,
            "tests_passed": tests_passed,
        }

    def _run_agent(self, repo_dir: Path, prompt: str, logs: list[str]) -> str:
        if self.preferred_engine == "openclaude" and shutil.which("openclaude"):
            return self._run(["openclaude", "-p", "--agent", "Explore", prompt], repo_dir, logs, check=False)
        if self.preferred_engine == "opencode" and shutil.which("opencode"):
            return self._run(["opencode", "run", prompt], repo_dir, logs, check=False)
        if shutil.which("codex"):
            return self._run(["codex", "exec", "-C", str(repo_dir), prompt], repo_dir, logs, check=False)
        logs.append("No local agent engine found; using deterministic fallback.")
        return ""

    def _run_tests(self, repo_dir: Path, commands: list[str], logs: list[str]) -> bool:
        if not commands:
            index = self._index_repo(repo_dir, logs)
            commands = index.get("test_commands") or []
        ok = True
        for command in commands[:3]:
            result = self._run(command, repo_dir, logs, shell=True, check=False)
            ok = ok and "exit code: 0" in result
        return ok

    def _heartbeat(self, job_id: str, claim_token: str, logs: str) -> None:
        self.client.post(
            f"/api/worker/jobs/{job_id}/heartbeat",
            {"worker_id": self.worker_id, "claim_token": claim_token, "logs": logs},
        )

    def _walk(self, root: Path):
        for path in root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                continue
            if path.is_file():
                yield path

    def _repo_dir(self, project: dict[str, Any]) -> Path:
        return self.workspace_root / self._slug(project["repo_full_name"])

    def _detect_stack(self, path: Path, content: str) -> set[str]:
        stack: set[str] = set()
        if path.name == "package.json":
            data = json.loads(content or "{}")
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for name in ["svelte", "react", "vue", "next", "vite", "express", "typescript"]:
                if name in deps:
                    stack.add(name)
        if path.name == "pyproject.toml":
            for name in ["fastapi", "django", "flask", "pytest"]:
                if name in content.lower():
                    stack.add(name)
            stack.add("python")
        if path.name in {"requirements.txt", "go.mod", "Cargo.toml"}:
            stack.add(path.suffix.lstrip(".") or path.name)
        return stack

    def _detect_test_commands(self, manifests: list[dict[str, str]]) -> list[str]:
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
            if manifest["path"].endswith("pyproject.toml") or manifest["path"].endswith("requirements.txt"):
                commands.append("python -m pytest")
        return commands

    def _detect_risks(self, repo_dir: Path, manifests: list[dict[str, str]], inventory: list[dict[str, Any]]) -> list[str]:
        risks: list[str] = []
        if not any(item["path"].lower().startswith(".github/workflows/") for item in inventory):
            risks.append("No GitHub Actions workflow detected.")
        if not any("test" in item["path"].lower() for item in inventory):
            risks.append("No obvious tests detected.")
        if any(item["path"].endswith(".env") for item in inventory):
            risks.append("Environment file is present in the repository inventory; verify secrets are not committed.")
        if not manifests:
            risks.append("No common dependency manifest detected.")
        return risks

    def _kind(self, path: Path) -> str:
        if path.name in MANIFEST_NAMES:
            return "manifest"
        if path.suffix.lower() in SOURCE_SUFFIXES:
            return "source"
        if path.suffix.lower() in {".md", ".txt", ".rst"}:
            return "doc"
        return "asset"

    def _fallback_summary(self, index: dict[str, Any]) -> str:
        return (
            "# Codebase Dossier\n\n"
            f"- Files indexed: {len(index.get('file_inventory', []))}\n"
            f"- Detected stack: {', '.join(index.get('detected_stack', [])) or 'unknown'}\n"
            f"- Test commands: {', '.join(index.get('test_commands', [])) or 'none detected'}\n\n"
            "## Risks\n"
            + "\n".join(f"- {risk}" for risk in index.get("risks", []))
        )

    def _read_text(self, path: Path, limit: int) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
        except OSError:
            return ""

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

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "repo"


def main() -> int:
    parser = argparse.ArgumentParser(description="Idea Refinery local worker")
    parser.add_argument("--once", action="store_true", help="Claim and run at most one job")
    parser.add_argument("--poll-seconds", type=int, default=int(os.getenv("IDEAREFINERY_WORKER_POLL_SECONDS", "60")))
    parser.add_argument("--api-base", default=os.getenv("IDEAREFINERY_API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.getenv("IDEAREFINERY_WORKER_AUTH_TOKEN", ""))
    parser.add_argument("--worker-id", default=os.getenv("IDEAREFINERY_WORKER_ID", os.environ.get("COMPUTERNAME", "local-worker")))
    parser.add_argument("--workspace-root", default=os.getenv("IDEAREFINERY_WORKER_WORKSPACE", str(Path.home() / ".idearefinery-worker" / "repos")))
    parser.add_argument("--engine", default=os.getenv("IDEAREFINERY_WORKER_ENGINE", "openclaude"))
    args = parser.parse_args()

    worker = IdeaRefineryWorker(
        api_base=args.api_base,
        worker_id=args.worker_id,
        token=args.token,
        workspace_root=Path(args.workspace_root),
        preferred_engine=args.engine,
    )

    while True:
        try:
            did_work = worker.run_once()
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"worker connection unavailable: {exc}", file=sys.stderr)
            did_work = False
        if args.once:
            return 0
        sleep_for = args.poll_seconds if not did_work else 5
        time.sleep(max(5, sleep_for + random.randint(-5, 8)))


if __name__ == "__main__":
    raise SystemExit(main())
