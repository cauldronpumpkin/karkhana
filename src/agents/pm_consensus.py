"""PM Consensus Agent - merges multiple PRDs into a single cohesive PRD."""

from src.agents.base import BaseAgent
from src.utils.prompts import PM_CONSENSUS_SYSTEM_PROMPT
from src.utils.parser import extract_json
import json


class PMConsensusAgent(BaseAgent):
    """Principal Product Manager agent that merges PRDs."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.5  # Lower temperature for analytical merging role

    async def merge_prds(self, prds: list[dict]) -> dict:
        """Merge a list of PRDs into a single master PRD."""
        
        prds_text = "\n\n---\n\n".join(
            [f"PRD DRAFT {i+1}:\n{json.dumps(prd, indent=2)}" for i, prd in enumerate(prds)]
        )

        messages = [
            {"role": "system", "content": PM_CONSENSUS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Please merge the following PRD drafts into a single master PRD:\n\n{prds_text}"
            }
        ]

        response = await self.generate(
            messages,
            temperature=self.temperature
        )

        return extract_json(response) or prds[0]
