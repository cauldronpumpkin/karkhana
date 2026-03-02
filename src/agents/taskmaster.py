"""Taskmaster Agent - manages file implementation queue."""

from typing import Any

from src.agents.base import BaseAgent
from src.utils.prompts import TASKMASTER_SYSTEM_PROMPT
from src.types.state import WorkingState


class Taskmaster(BaseAgent):
    """Manages the file implementation queue."""

    def __init__(self):
        super().__init__()
        self.temperature = 0.1

    def generate_coordination_requests(
        self,
        *,
        all_files: list[str],
        pending_files: list[str],
        completed_files: set[str],
    ) -> list[dict[str, Any]]:
        """Emit sequencing/decomposition clarifications when ordering is unclear."""
        _ = completed_files
        if not all_files:
            return []

        # If many files are pending with no explicit ordering hints, ask for sequencing guidance.
        if len(pending_files) >= 6 and not any("index" in file or "main" in file for file in pending_files):
            return [
                {
                    "from_agent": "taskmaster",
                    "message_type": "clarification_request",
                    "topic": "task_ordering",
                    "blocking": False,
                    "content_json": {
                        "area": "requirements",
                        "question": "Multiple files are pending with ambiguous priority.",
                        "pending_count": len(pending_files),
                    },
                }
            ]
        return []

    async def get_next_file(self, state: WorkingState) -> str | None:
        """Determine the next file to implement."""
        if not state.file_tree:
            return None
        
        # Flatten file tree into ordered list
        all_files = []
        for directory, files in state.file_tree.items():
            for file in files:
                full_path = f"{directory.rstrip('/')}/{file}"
                if full_path not in state.completed_files:
                    all_files.append(full_path)
        
        # Return first pending file
        return all_files[0] if all_files else None

    async def parse_file_tree(self, architecture: dict) -> list[str]:
        """Parse architecture output into file list."""
        file_list = []
        
        if "file_tree" in architecture:
            for directory, files in architecture["file_tree"].items():
                for file in files:
                    full_path = f"{directory.rstrip('/')}/{file}"
                    file_list.append(full_path)
        
        return file_list
