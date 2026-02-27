"""Reviewer Agent - validates code quality and syntax."""

from src.agents.base import BaseAgent
from src.utils.prompts import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT
from src.utils.parser import extract_json


class ReviewerAgent(BaseAgent):
    """Reviews code for quality, syntax, and hallucinations."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.1

    async def review_code(
        self,
        file_path: str,
        code_content: str,
        project_context: dict
    ) -> dict:
        """Review a single file's code."""
        messages = [
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": REVIEWER_USER_PROMPT.format(
                    file_path=file_path,
                    code_content=code_content,
                    project_context=str(project_context)
                )
            }
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        return extract_json(response) or {
            "passed": False,
            "issues": [{"type": "unknown", "description": "Could not parse review result"}]
        }
