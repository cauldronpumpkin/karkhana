"""Workflow manager for karkhana."""

import json
import uuid
from typing import Any
from pathlib import Path

WORKFLOWS_FILE = Path(__file__).parent.parent.parent / "workflows.json"

# Available environment variables that can be injected into agents
DEFAULT_ENV_VARS = [
    {"key": "LM_STUDIO_BASE_URL", "label": "LM Studio Base URL"},
    {"key": "LM_STUDIO_MODEL_NAME", "label": "LM Studio Model Name"},
    {"key": "MAX_TOKENS", "label": "Max Tokens"},
    {"key": "TEMPERATURE_CREATIVE", "label": "Temperature (Creative)"},
    {"key": "TEMPERATURE_CODING", "label": "Temperature (Coding)"},
    {"key": "TIMEOUT_SECONDS", "label": "Timeout Seconds"},
    {"key": "MAX_RETRIES", "label": "Max Retries"},
    {"key": "SANDBOX_TIMEOUT", "label": "Sandbox Timeout"},
    {"key": "MAX_RETRIES_PER_FILE", "label": "Max Retries Per File"},
    {"key": "TOOL_CALLING_ENABLED", "label": "Tool Calling Enabled"},
    {"key": "TOOL_CALLING_FALLBACK_ENABLED", "label": "Tool Calling Fallback Enabled"},
    {"key": "TOOL_CALLING_MAX_ROUNDS", "label": "Tool Calling Max Rounds"},
    {"key": "TOOL_CALLING_FILE_TOOL_MAX_CHARS", "label": "Tool Read Max Chars"},
]

class WorkflowManager:
    """Manages CRUD operations for custom workflows (sequences of agents)."""

    def __init__(self):
        self.workflows_file = WORKFLOWS_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not self.workflows_file.exists():
            default_workflows = [
                {
                    "id": "standard-factory",
                    "name": "Standard Software Factory",
                    "steps": ["pm-agent-1", "lead-agent-1", "backend-eng-1", "frontend-eng-1"],
                    "description": "The default multi-agent pipeline.",
                    "env_vars": {},
                    "agent_qualities": {}
                }
            ]
            with open(self.workflows_file, "w", encoding="utf-8") as f:
                json.dump(default_workflows, f, indent=2)

    def get_all(self) -> list[dict[str, Any]]:
        try:
            with open(self.workflows_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def get(self, workflow_id: str) -> dict[str, Any] | None:
        workflows = self.get_all()
        for w in workflows:
            if w.get("id") == workflow_id:
                return w
        return None

    def create(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        workflows = self.get_all()
        workflow = {
            "id": str(uuid.uuid4())[:12],
            "name": workflow_data.get("name", "Untitled Workflow"),
            "steps": workflow_data.get("steps", []),
            "description": workflow_data.get("description", ""),
            "env_vars": workflow_data.get("env_vars", {}),
            "agent_qualities": workflow_data.get("agent_qualities", {}),
            "conditions": workflow_data.get("conditions", {}),
            "loops": workflow_data.get("loops", {})
        }
        workflows.append(workflow)
        with open(self.workflows_file, "w", encoding="utf-8") as f:
            json.dump(workflows, f, indent=2)
        return workflow

    def delete(self, workflow_id: str) -> bool:
        workflows = self.get_all()
        initial_length = len(workflows)
        workflows = [w for w in workflows if w.get("id") != workflow_id]
        if len(workflows) < initial_length:
            with open(self.workflows_file, "w", encoding="utf-8") as f:
                json.dump(workflows, f, indent=2)
            return True
        return False
