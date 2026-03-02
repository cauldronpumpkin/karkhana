"""Dynamic Agent definition."""

from typing import Any
from src.agents.base import BaseAgent
from src.utils.parser import extract_json

class DynamicAgent(BaseAgent):
    """An agent initialized from a generic template."""

    def __init__(self, template: dict[str, Any]):
        super().__init__()
        self.template = template
        self.temperature = template.get("temperature", 0.7)
        self.system_prompt = template.get("system_prompt", "You are a helpful assistant.")
        self.user_prompt_template = template.get("user_prompt_template", "{input}")

    async def run(self, inputs: dict[str, Any]) -> str | dict:
        """Run the dynamic agent with given inputs."""
        
        user_prompt = self.user_prompt_template.format(**inputs) 

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        # Try to parse as JSON if the prompt implies it, else return raw
        if "json" in self.system_prompt.lower() or "json" in self.user_prompt_template.lower():
            parsed = extract_json(response)
            if parsed:
                return parsed
        
        return response
