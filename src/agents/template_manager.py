"""Template manager for dynamic agents."""

import json
import os
import uuid
from typing import Any
from pathlib import Path

# Use a local file to store custom templates for simplicity
TEMPLATES_FILE = Path(__file__).parent.parent.parent / "agent_templates.json"

class TemplateManager:
    """Manages CRUD operations for dynamic agent templates."""

    def __init__(self):
        self.templates_file = TEMPLATES_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not self.templates_file.exists():
            default_templates = [
                {
                    "id": "builtin-summarizer",
                    "name": "Summarizer Agent",
                    "system_prompt": "You are an expert summarizer. Summarize the user's input concisely.",
                    "user_prompt_template": "Please summarize the following text:\n\n{input}",
                    "temperature": 0.3
                }
            ]
            with open(self.templates_file, "w", encoding="utf-8") as f:
                json.dump(default_templates, f, indent=2)
                
    def get_all(self) -> list[dict[str, Any]]:
        self._ensure_file()
        try:
            with open(self.templates_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
            
    def get(self, template_id: str) -> dict[str, Any] | None:
        templates = self.get_all()
        for t in templates:
            if t.get("id") == template_id:
                return t
        return None
        
    def create(self, template_data: dict[str, Any]) -> dict[str, Any]:
        templates = self.get_all()
        template = {
            "id": str(uuid.uuid4())[:8],
            "name": template_data.get("name", "Unnamed Agent"),
            "system_prompt": template_data.get("system_prompt", "You are a helpful assistant."),
            "user_prompt_template": template_data.get("user_prompt_template", "{input}"),
            "temperature": template_data.get("temperature", 0.7)
        }
        templates.append(template)
        with open(self.templates_file, "w", encoding="utf-8") as f:
            json.dump(templates, f, indent=2)
        return template
        
    def delete(self, template_id: str) -> bool:
        templates = self.get_all()
        initial_length = len(templates)
        templates = [t for t in templates if t.get("id") != template_id]
        if len(templates) < initial_length:
            with open(self.templates_file, "w", encoding="utf-8") as f:
                json.dump(templates, f, indent=2)
            return True
        return False
