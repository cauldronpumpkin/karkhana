"""Idea manager for karkhana."""

import json
import uuid
from typing import Any
from pathlib import Path

IDEAS_FILE = Path(__file__).parent.parent.parent / "ideas.json"

class IdeaManager:
    """Manages CRUD operations for ideas and their associated pipeline runs."""

    def __init__(self):
        self.ideas_file = IDEAS_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not self.ideas_file.exists():
            with open(self.ideas_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_all(self) -> list[dict[str, Any]]:
        try:
            with open(self.ideas_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def get(self, idea_id: str) -> dict[str, Any] | None:
        ideas = self.get_all()
        for i in ideas:
            if i.get("id") == idea_id:
                return i
        return None

    def create(self, idea_text: str) -> dict[str, Any]:
        ideas = self.get_all()
        idea = {
            "id": str(uuid.uuid4())[:12],
            "text": idea_text,
            "pipeline_runs": []  # List of run histories/statuses
        }
        ideas.append(idea)
        with open(self.ideas_file, "w", encoding="utf-8") as f:
            json.dump(ideas, f, indent=2)
        return idea

    def delete(self, idea_id: str) -> bool:
        ideas = self.get_all()
        initial_length = len(ideas)
        ideas = [i for i in ideas if i.get("id") != idea_id]
        if len(ideas) < initial_length:
            with open(self.ideas_file, "w", encoding="utf-8") as f:
                json.dump(ideas, f, indent=2)
            return True
        return False

    def add_run(self, idea_id: str, run_data: dict[str, Any]):
        ideas = self.get_all()
        for i in ideas:
            if i.get("id") == idea_id:
                if "pipeline_runs" not in i:
                    i["pipeline_runs"] = []
                i["pipeline_runs"].append(run_data)
                break
        with open(self.ideas_file, "w", encoding="utf-8") as f:
            json.dump(ideas, f, indent=2)
