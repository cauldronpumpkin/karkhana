"""PM Agent - generates Product Requirement Documents from raw ideas."""

from src.agents.base import BaseAgent
from src.utils.prompts import PM_SYSTEM_PROMPT, PM_USER_PROMPT
from src.utils.parser import extract_json


class PMAgent(BaseAgent):
    """Product Manager agent that generates structured PRDs."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.7

    async def generate_prd(self, raw_idea: str) -> dict:
        """Generate a complete PRD from a raw idea."""
        messages = [
            {"role": "system", "content": PM_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": PM_USER_PROMPT.format(raw_idea=raw_idea)
            }
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        return extract_json(response) or {"raw_idea": raw_idea}
