"""Sandbox executor for safe subprocess execution."""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path


class SandboxExecutor:
    """Execute commands in an isolated sandbox environment."""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    async def execute(
        self,
        command: list[str],
        working_dir: Path,
        env_vars: dict[str, str] | None = None
    ) -> tuple[int, str, str]:
        """Execute command in isolated temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Copy project files to temp dir
            if working_dir.exists():
                shutil.copytree(
                    working_dir,
                    tmp_path / "project",
                    dirs_exist_ok=True
                )
            
            # Prepare environment
            exec_env = os.environ.copy()
            exec_env["NO_INTERNET"] = "1"
            if env_vars:
                exec_env.update(env_vars)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=tmp_path / "project",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=exec_env
                )
                
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout
                )
                
                return (
                    proc.returncode or 0,
                    stdout.decode("utf-8", errors="replace"),
                    stderr.decode("utf-8", errors="replace")
                )
                
            except asyncio.TimeoutError:
                if proc.pid:
                    try:
                        os.kill(proc.pid, 9)
                    except ProcessLookupError:
                        pass
                return (
                    -1,
                    "",
                    f"Timeout: command exceeded {self.timeout}s limit"
                )

    async def execute_python(
        self,
        file_path: Path,
        working_dir: Path
    ) -> tuple[int, str, str]:
        """Execute Python file in sandbox."""
        return await self.execute(
            ["python", str(file_path)],
            working_dir
        )

    async def execute_test_suite(
        self,
        test_command: str,
        working_dir: Path
    ) -> tuple[int, str, str]:
        """Execute test suite (pytest or jest)."""
        if "test" in test_command.lower():
            return await self.execute(
                ["python", "-m", "pytest", test_command],
                working_dir
            )
        return await self.execute(
            test_command.split(),
            working_dir
        )
