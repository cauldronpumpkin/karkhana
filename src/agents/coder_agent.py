"""Coder Agent - writes implementation for individual files."""

import os
from pathlib import Path

from src.agents.base import BaseAgent
from src.utils.prompts import (
    CODER_SYSTEM_PROMPT,
    CODER_USER_PROMPT,
    CODER_SELF_HEAL_PROMPT
)
from src.utils.parser import extract_code_block


class CoderAgent(BaseAgent):
    """Writes code for individual files."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.2

    async def write_file(
        self,
        file_path: str,
        prd_context: dict,
        tech_stack: dict,
        requirements: list[str],
        existing_files: dict[str, str]
    ) -> str:
        """Generate code for a single file."""
        language = self._detect_language(file_path)
        
        context = f"""
- Project Type: {prd_context.get('title', 'Generic Project')}
- PRD Goal: {prd_context.get('problem_statement', '')}
- Tech Stack: {tech_stack.get('frontend', {})}
"""
        
        # Format requirements
        req_text = "\n".join([f"- {r}" for r in requirements]) if requirements else "Implement clean, production-ready code."

        # Format existing files
        existing_text = ""
        for path, content in existing_files.items():
            existing_text += f"\n\n# File: {path}\n{content[:500]}..."

        messages = [
            {"role": "system", "content": CODER_SYSTEM_PROMPT},
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
                )
            }
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        return extract_code_block(response)

    async def self_heal(
        self,
        file_path: str,
        error_message: str,
        traceback: str,
        current_code: str
    ) -> str:
        """Attempt to fix code based on error."""
        messages = [
            {"role": "system", "content": CODER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": CODER_SELF_HEAL_PROMPT.format(
                    file_path=file_path,
                    error_message=error_message,
                    traceback=traceback
                )
            }
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        return extract_code_block(response)

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
