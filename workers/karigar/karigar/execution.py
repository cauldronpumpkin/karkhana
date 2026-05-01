from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from subprocess import PIPE, Popen
from shlex import split as shlex_split


@dataclass(slots=True)
class CommandExecution:
    command: str
    return_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


class CommandRunner:
    def run(self, command: str, timeout_seconds: int, cwd: str | None = None, env: dict[str, str] | None = None) -> CommandExecution:
        raise NotImplementedError


class MockCommandRunner(CommandRunner):
    def run(self, command: str, timeout_seconds: int, cwd: str | None = None, env: dict[str, str] | None = None) -> CommandExecution:
        return CommandExecution(command=command, return_code=0, stdout=f"mocked: {command}", stderr="", duration_seconds=0.0)


class SystemCommandRunner(CommandRunner):
    def run(self, command: str, timeout_seconds: int, cwd: str | None = None, env: dict[str, str] | None = None) -> CommandExecution:
        start = monotonic()
        proc = Popen(shlex_split(command), cwd=cwd, env=env, stdout=PIPE, stderr=PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
            timed_out = False
        except Exception:
            proc.kill()
            stdout, stderr = proc.communicate()
            timed_out = True
        return CommandExecution(command=command, return_code=proc.returncode or 0, stdout=stdout or "", stderr=stderr or "", duration_seconds=monotonic() - start, timed_out=timed_out)
