"""Coder Agent - writes implementation for individual files."""

import os
from typing import Any

from src.agents.base import BaseAgent
from src.config import config
from src.utils.prompts import (
    CODER_SYSTEM_PROMPT,
    CODER_USER_PROMPT,
    CODER_SELF_HEAL_PROMPT,
    CODER_TESTS_PROMPT,
    CODER_IMPL_FROM_TESTS_PROMPT,
    with_thinking_modules,
)
from src.utils.parser import extract_code_block, extract_tag_block


class CoderAgent(BaseAgent):
    """Writes code for individual files."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.2

    def _tool_calling_enabled(self) -> bool:
        return bool(config.tool_calling.enabled)

    def _tool_instruction_suffix(self) -> str:
        return (
            "\n\n## Tool Usage\n"
            "You can call available tools before answering.\n"
            "- Use `list_files` to inspect available project files.\n"
            "- Use `read_file` with an exact `path` to inspect file content.\n"
            "Call tools only when they materially improve implementation quality."
        )

    def _build_file_tools(self, existing_files: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        max_chars = int(config.tool_calling.file_tool_max_chars)
        file_map = dict(existing_files or {})

        def list_files(_args: dict[str, Any]) -> dict[str, Any]:
            paths = sorted(file_map.keys())
            return {"count": len(paths), "paths": paths}

        def read_file(args: dict[str, Any]) -> dict[str, Any]:
            path = str((args or {}).get("path", "")).strip()
            if not path:
                return {"ok": False, "error": "missing_path", "message": "Required argument `path` is missing."}
            if path not in file_map:
                return {"ok": False, "error": "not_found", "path": path}
            content = str(file_map[path] or "")
            trimmed = content[:max_chars]
            return {
                "ok": True,
                "path": path,
                "content": trimmed,
                "truncated": len(trimmed) < len(content),
                "total_chars": len(content),
            }

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List available project file paths currently in memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read one project file by exact path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Exact file path returned by list_files.",
                            }
                        },
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
        ]
        handlers = {
            "list_files": list_files,
            "read_file": read_file,
        }
        return tools, handlers

    async def _generate_with_file_tools(
        self,
        messages: list[dict[str, Any]],
        *,
        existing_files: dict[str, str],
        temperature: float,
    ) -> str:
        if not self._tool_calling_enabled():
            return await self.generate(messages, temperature=temperature)

        tools, handlers = self._build_file_tools(existing_files)
        return await self.generate(
            messages,
            temperature=temperature,
            tools=tools,
            tool_handlers=handlers,
            tool_choice="auto",
            max_tool_rounds=int(config.tool_calling.max_rounds),
            fallback_tool_parsing=bool(config.tool_calling.fallback_enabled),
        )

    def generate_coordination_requests(
        self,
        *,
        file_path: str,
        requirements: list[str],
        prd_context: dict[str, Any],
        resolved_requests: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Emit structured coordination requests before coding when needed."""
        _ = prd_context
        resolved_requests = resolved_requests or []
        resolved_topics = {
            str(item.get("topic"))
            for item in resolved_requests
            if isinstance(item, dict)
        }

        requests: list[dict[str, Any]] = []

        if (not requirements or all(not r.strip() for r in requirements)) and "requirements_scope" not in resolved_topics:
            requests.append(
                {
                    "from_agent": "coder_agent",
                    "message_type": "clarification_request",
                    "topic": "requirements_scope",
                    "blocking": True,
                    "content_json": {
                        "area": "requirements",
                        "question": f"Requirements are ambiguous for {file_path}.",
                    },
                }
            )

        return requests

    async def write_file(
        self,
        file_path: str,
        prd_context: dict,
        tech_stack: dict,
        requirements: list[str],
        existing_files: dict[str, str],
        *,
        thinking_modules_enabled: bool = False,
    ) -> dict[str, str]:
        """Generate code for a single file."""
        language = self._detect_language(file_path)
        
        # Format requirements
        req_text = "\n".join([f"- {r}" for r in requirements]) if requirements else "Implement clean, production-ready code."

        # Format existing files
        existing_text = ""
        for path, content in existing_files.items():
            existing_text += f"\n\n# File: {path}\n{content[:500]}..."

        system_prompt = CODER_SYSTEM_PROMPT
        if thinking_modules_enabled:
            system_prompt = with_thinking_modules(system_prompt, "code_output")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": CODER_USER_PROMPT.format(
                    language=language,
                    file_path=file_path,
                    project_type=prd_context.get('title', 'Generic Project'),
                    prd_goal=prd_context.get('problem_statement', ''),
                    tech_stack=str(tech_stack),
                    requirements=req_text,
                    existing_files=existing_text
                ) + (self._tool_instruction_suffix() if self._tool_calling_enabled() else "")
            }
        ]

        response = await self._generate_with_file_tools(
            messages,
            existing_files=existing_files,
            temperature=self.temperature,
        )

        return {
            "code": extract_code_block(response),
            "thinking": (extract_tag_block(response, "thinking") or "")[:12000],
        }

    async def write_tests(
        self,
        *,
        file_path: str,
        prd_context: dict[str, Any],
        tech_stack: dict[str, Any],
        requirements: list[str],
        existing_files: dict[str, str],
        thinking_modules_enabled: bool = False,
    ) -> dict[str, str]:
        """Generate tests first for TDD reflection loops."""
        language = self._detect_language(file_path)
        req_text = "\n".join([f"- {r}" for r in requirements]) if requirements else "Cover core behavior and edge cases."
        existing_text = ""
        for path, content in existing_files.items():
            existing_text += f"\n\n# File: {path}\n{content[:500]}..."

        system_prompt = CODER_SYSTEM_PROMPT
        if thinking_modules_enabled:
            system_prompt = with_thinking_modules(system_prompt, "code_output")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": CODER_TESTS_PROMPT.format(
                    file_path=file_path,
                    language=language,
                    project_type=prd_context.get("title", "Generic Project"),
                    prd_goal=prd_context.get("problem_statement", ""),
                    tech_stack=str(tech_stack),
                    requirements=req_text,
                    existing_files=existing_text,
                ) + (self._tool_instruction_suffix() if self._tool_calling_enabled() else ""),
            },
        ]
        response = await self._generate_with_file_tools(
            messages,
            existing_files=existing_files,
            temperature=self.temperature,
        )
        return {
            "code": extract_code_block(response),
            "thinking": (extract_tag_block(response, "thinking") or "")[:12000],
        }

    async def write_impl_from_tests(
        self,
        *,
        file_path: str,
        test_file_path: str,
        test_code: str,
        prd_context: dict[str, Any],
        requirements: list[str],
        existing_files: dict[str, str],
        thinking_modules_enabled: bool = False,
    ) -> dict[str, str]:
        """Generate implementation guided by generated tests."""
        language = self._detect_language(file_path)
        req_text = "\n".join([f"- {r}" for r in requirements]) if requirements else "Satisfy tests robustly."
        existing_text = ""
        for path, content in existing_files.items():
            existing_text += f"\n\n# File: {path}\n{content[:500]}..."

        system_prompt = CODER_SYSTEM_PROMPT
        if thinking_modules_enabled:
            system_prompt = with_thinking_modules(system_prompt, "code_output")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": CODER_IMPL_FROM_TESTS_PROMPT.format(
                    file_path=file_path,
                    language=language,
                    test_file_path=test_file_path,
                    test_code=test_code,
                    requirements=req_text,
                    existing_files=existing_text,
                ) + (self._tool_instruction_suffix() if self._tool_calling_enabled() else ""),
            },
        ]
        response = await self._generate_with_file_tools(
            messages,
            existing_files=existing_files,
            temperature=self.temperature,
        )
        return {
            "code": extract_code_block(response),
            "thinking": (extract_tag_block(response, "thinking") or "")[:12000],
        }

    async def repair_from_test_failure(
        self,
        *,
        file_path: str,
        test_file_path: str,
        test_code: str,
        stderr: str,
        current_code: str,
        iteration_context: str,
        thinking_modules_enabled: bool = False,
    ) -> dict[str, str]:
        """Repair implementation using raw stderr from failed tests."""
        system_prompt = CODER_SYSTEM_PROMPT
        if thinking_modules_enabled:
            system_prompt = with_thinking_modules(system_prompt, "code_output")
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"The tests failed for {file_path}.\n\n"
                    f"Test file: {test_file_path}\n\n"
                    f"Test code:\n{test_code}\n\n"
                    f"Current implementation:\n{current_code}\n\n"
                    f"Raw stderr:\n{stderr}\n\n"
                    f"Iteration context:\n{iteration_context}\n\n"
                    "Return the fully fixed implementation file only."
                ) + (self._tool_instruction_suffix() if self._tool_calling_enabled() else ""),
            },
        ]
        response = await self._generate_with_file_tools(
            messages,
            existing_files={test_file_path: test_code, file_path: current_code},
            temperature=self.temperature,
        )
        return {
            "code": extract_code_block(response),
            "thinking": (extract_tag_block(response, "thinking") or "")[:12000],
        }

    async def self_heal(
        self,
        file_path: str,
        error_message: str,
        traceback: str,
        current_code: str,
        *,
        thinking_modules_enabled: bool = False,
    ) -> dict[str, str]:
        """Attempt to fix code based on error."""
        system_prompt = CODER_SYSTEM_PROMPT
        if thinking_modules_enabled:
            system_prompt = with_thinking_modules(system_prompt, "code_output")
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": CODER_SELF_HEAL_PROMPT.format(
                    file_path=file_path,
                    error_message=error_message,
                    traceback=traceback
                ) + (self._tool_instruction_suffix() if self._tool_calling_enabled() else "")
            }
        ]

        response = await self._generate_with_file_tools(
            messages,
            existing_files={file_path: current_code},
            temperature=self.temperature,
        )

        return {
            "code": extract_code_block(response),
            "thinking": (extract_tag_block(response, "thinking") or "")[:12000],
        }

    def test_file_for(self, file_path: str) -> str:
        """Infer a test file path based on file extension."""
        base, ext = os.path.splitext(file_path)
        language = self._detect_language(file_path)
        if language == "python":
            return f"tests/test_{base.replace('/', '_').replace('-', '_')}.py"
        if language in {"javascript", "typescript"}:
            return f"tests/{base}.test{ext or '.js'}"
        return f"tests/{base}.test.txt"

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".json": "json",
            ".md": "markdown"
        }
        
        ext = os.path.splitext(file_path)[1].lower()
        return ext_map.get(ext, "unknown")
