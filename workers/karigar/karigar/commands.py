from __future__ import annotations

from dataclasses import dataclass
from shlex import split as shlex_split
from typing import Iterable


@dataclass(frozen=True, slots=True)
class SafeCommandPolicy:
    """Minimal command allow-list for the mock runner."""

    allowed_prefixes: tuple[str, ...] = ("python", "pytest", "git status", "git diff", "git rev-parse", "graphify update")
    denied_prefixes: tuple[str, ...] = ("rm ", "del ", "rmdir ", "move ", "rename ", "git merge", "git rebase", "git reset", "git push", "git pull", "powershell")

    def is_allowed(self, command: str) -> bool:
        """Return whether the command is permitted."""

        normalized = command.strip().lower()
        if self.is_denied(command):
            return False
        return any(normalized == prefix or normalized.startswith(f"{prefix} ") for prefix in self.allowed_prefixes)

    def is_denied(self, command: str) -> bool:
        normalized = command.strip().lower()
        return any(normalized == prefix.strip() or normalized.startswith(prefix) for prefix in self.denied_prefixes)

    def split_command(self, command: str) -> list[str]:
        return list(shlex_split(command))

    def iter_verified_commands(self, commands: Iterable[str]) -> list[str]:
        return [command.strip() for command in commands if command.strip()]
