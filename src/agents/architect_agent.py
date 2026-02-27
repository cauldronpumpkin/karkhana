"""Architect Agent - defines tech stack and file structure."""

from src.agents.base import BaseAgent
from src.utils.prompts import ARCHITECT_SYSTEM_PROMPT, ARCHITECT_USER_PROMPT
from src.utils.parser import extract_json


class ArchitectAgent(BaseAgent):
    """Software Architect agent that defines tech stack and file tree."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.5

    async def generate_architecture(self, prd: dict) -> dict:
        """Generate architecture based on PRD."""
        prd_content = f"""
Title: {prd.get('title', 'N/A')}
Problem: {prd.get('problem_statement', 'N/A')}
Features: {prd.get('core_features', [])}
Constraints: {prd.get('technical_constraints', [])}
"""
        
        messages = [
            {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": ARCHITECT_USER_PROMPT.format(prd_content=prd_content)
            }
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        return extract_json(response) or {}
