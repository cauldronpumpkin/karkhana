"""Reviewer Agent - validates code quality and syntax."""

from typing import Any

from src.agents.base import BaseAgent
from src.utils.prompts import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT
from src.utils.parser import extract_json


class ReviewerAgent(BaseAgent):
    """Reviews code for quality, syntax, and hallucinations."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.1

    def generate_coordination_requests(
        self,
        *,
        file_path: str,
        review_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Emit structured follow-up requests based on review outcome."""
        requests: list[dict[str, Any]] = []
        passed = bool(review_result.get("passed", False))
        issues = review_result.get("issues", []) or []
        if passed:
            return requests

        issue_text = " ".join(str(issue).lower() for issue in issues)
        if any(token in issue_text for token in ("requirement", "scope", "mismatch")):
            requests.append(
                {
                    "from_agent": "reviewer_agent",
                    "message_type": "clarification_request",
                    "topic": f"review_requirements_{file_path}",
                    "blocking": True,
                    "content_json": {
                        "area": "requirements",
                        "question": f"Reviewer found requirement mismatch in {file_path}.",
                        "issues": issues,
                    },
                }
            )

        if any(token in issue_text for token in ("dependency", "security", "unsafe", "vulnerability")):
            requests.append(
                {
                    "from_agent": "reviewer_agent",
                    "message_type": "dependency_approval_request",
                    "topic": f"review_dependency_{file_path}",
                    "blocking": True,
                    "content_json": {
                        "dependency": "unknown",
                        "security_concern": True,
                        "issues": issues,
                    },
                }
            )

        return requests

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
