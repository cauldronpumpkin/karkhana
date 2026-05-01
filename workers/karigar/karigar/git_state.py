from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from subprocess import run


@dataclass(slots=True)
class GitState:
    """Best-effort git metadata for a workspace."""

    root: Path
    is_repo: bool
    branch: str | None = None
    commit_sha: str | None = None
    diff_path: str | None = None
    dirty: bool = False
    changed_files: list[str] = field(default_factory=list)
    code_or_docs_changed: bool = False

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "root": str(self.root),
            "is_repo": self.is_repo,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "diff_path": self.diff_path,
            "dirty": self.dirty,
            "changed_files": self.changed_files,
            "code_or_docs_changed": self.code_or_docs_changed,
        }


def detect_git_state(root: Path) -> GitState:
    if not root.exists() or not (root / ".git").exists():
        return GitState(root=root, is_repo=False)
    branch = _run_git(root, ["branch", "--show-current"])
    commit_sha = _run_git(root, ["rev-parse", "HEAD"])
    status = _run_git(root, ["status", "--porcelain"])
    changed_files = [line[3:] for line in status.splitlines() if len(line) > 3]
    code_or_docs_changed = any(path.endswith((".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml")) for path in changed_files)
    return GitState(root=root, is_repo=True, branch=branch or None, commit_sha=commit_sha or None, dirty=bool(changed_files), changed_files=changed_files, code_or_docs_changed=code_or_docs_changed)


def _run_git(root: Path, args: list[str]) -> str:
    completed = run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return completed.stdout.strip()
