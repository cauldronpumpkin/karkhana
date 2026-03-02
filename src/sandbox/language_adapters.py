"""Language adapter registry for test/syntax commands in sandbox loops."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageAdapter:
    language: str

    def available(self) -> bool:
        raise NotImplementedError

    def generate_test_command(self, *, file_path: str, test_file_path: str) -> list[str]:
        raise NotImplementedError

    def generate_syntax_command(self, *, file_path: str) -> list[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class PythonAdapter(LanguageAdapter):
    language: str = "python"

    def available(self) -> bool:
        return bool(shutil.which("python"))

    def generate_test_command(self, *, file_path: str, test_file_path: str) -> list[str]:
        _ = file_path
        return ["python", "-m", "pytest", test_file_path]

    def generate_syntax_command(self, *, file_path: str) -> list[str]:
        return ["python", "-m", "py_compile", file_path]


@dataclass(frozen=True)
class JavaScriptAdapter(LanguageAdapter):
    language: str = "javascript"

    def available(self) -> bool:
        return bool(shutil.which("node"))

    def generate_test_command(self, *, file_path: str, test_file_path: str) -> list[str]:
        _ = file_path
        return ["node", test_file_path]

    def generate_syntax_command(self, *, file_path: str) -> list[str]:
        return ["node", "--check", file_path]


@dataclass(frozen=True)
class TypeScriptAdapter(LanguageAdapter):
    language: str = "typescript"

    def available(self) -> bool:
        return bool(shutil.which("npx") or shutil.which("tsc"))

    def generate_test_command(self, *, file_path: str, test_file_path: str) -> list[str]:
        compiler = "npx" if shutil.which("npx") else "tsc"
        if compiler == "npx":
            return ["npx", "tsc", "--noEmit", file_path, test_file_path]
        return ["tsc", "--noEmit", file_path, test_file_path]

    def generate_syntax_command(self, *, file_path: str) -> list[str]:
        compiler = "npx" if shutil.which("npx") else "tsc"
        if compiler == "npx":
            return ["npx", "tsc", "--noEmit", file_path]
        return ["tsc", "--noEmit", file_path]


_ADAPTERS: dict[str, LanguageAdapter] = {
    "python": PythonAdapter(),
    "javascript": JavaScriptAdapter(),
    "typescript": TypeScriptAdapter(),
}


def adapter_for_file(file_path: str) -> LanguageAdapter | None:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".py":
        return _ADAPTERS["python"]
    if ext in {".js", ".jsx"}:
        return _ADAPTERS["javascript"]
    if ext in {".ts", ".tsx"}:
        return _ADAPTERS["typescript"]
    return None
