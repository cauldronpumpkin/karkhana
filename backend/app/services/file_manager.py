from __future__ import annotations

import json
import re
from pathlib import Path


class FileManager:
    PHASE_REPORT_NUMBERS = {
        "capture": "01",
        "clarify": "02",
        "market_research": "03",
        "competitive_analysis": "04",
        "monetization": "05",
        "feasibility": "06",
        "tech_spec": "07",
        "build": "08",
    }

    def __init__(self, base_dir: Path | str = Path("data") / "ideas") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_idea_folder(self, slug: str) -> Path:
        idea_folder = self.get_idea_folder(slug)
        (idea_folder / "research" / "prompts").mkdir(parents=True, exist_ok=True)
        (idea_folder / "research" / "results").mkdir(parents=True, exist_ok=True)
        (idea_folder / "reports").mkdir(parents=True, exist_ok=True)
        return idea_folder

    def get_idea_folder(self, slug: str) -> Path:
        return self.base_dir / self._safe_slug(slug)

    def write_state(self, slug: str, state: dict) -> None:
        idea_folder = self.create_idea_folder(slug)
        state_path = idea_folder / "state.json"
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def read_state(self, slug: str) -> dict:
        state_path = self.get_idea_folder(slug) / "state.json"
        if not state_path.exists():
            return {}
        return json.loads(state_path.read_text(encoding="utf-8"))

    def save_research_prompt(self, slug: str, prompt: str, topic: str) -> str:
        prompts_dir = self.create_idea_folder(slug) / "research" / "prompts"
        next_number = self._next_research_number(prompts_dir)
        topic_slug = self._topic_slug(topic)
        filename = f"{next_number:03d}-{topic_slug}.md"
        (prompts_dir / filename).write_text(prompt, encoding="utf-8")
        return filename

    def save_research_result(self, slug: str, filename: str, content: str) -> Path:
        results_dir = self.create_idea_folder(slug) / "research" / "results"
        safe_name = Path(filename).name
        result_path = results_dir / safe_name
        result_path.write_text(content, encoding="utf-8")
        return result_path

    def get_pending_research(self, slug: str) -> list[dict]:
        prompts_dir = self.get_idea_folder(slug) / "research" / "prompts"
        results_dir = self.get_idea_folder(slug) / "research" / "results"
        if not prompts_dir.exists():
            return []

        pending: list[dict] = []
        for prompt_path in sorted(prompts_dir.glob("*.md")):
            if not (results_dir / prompt_path.name).exists():
                pending.append({"filename": prompt_path.name, "topic": self._topic_from_filename(prompt_path.name)})
        return pending

    def get_completed_research(self, slug: str) -> list[dict]:
        prompts_dir = self.get_idea_folder(slug) / "research" / "prompts"
        results_dir = self.get_idea_folder(slug) / "research" / "results"
        if not prompts_dir.exists():
            return []

        completed: list[dict] = []
        for prompt_path in sorted(prompts_dir.glob("*.md")):
            result_path = results_dir / prompt_path.name
            if result_path.exists():
                completed.append(
                    {
                        "prompt_filename": prompt_path.name,
                        "result_filename": result_path.name,
                        "topic": self._topic_from_filename(prompt_path.name),
                    }
                )
        return completed

    def write_report(self, slug: str, phase: str, content: str) -> None:
        report_number = self.PHASE_REPORT_NUMBERS.get(phase)
        if report_number is None:
            raise ValueError(f"Unknown phase: {phase}")
        reports_dir = self.create_idea_folder(slug) / "reports"
        (reports_dir / f"{report_number}-{phase}.md").write_text(content, encoding="utf-8")

    def read_report(self, slug: str, phase: str) -> str:
        report_number = self.PHASE_REPORT_NUMBERS.get(phase)
        if report_number is None:
            raise ValueError(f"Unknown phase: {phase}")
        report_path = self.get_idea_folder(slug) / "reports" / f"{report_number}-{phase}.md"
        if not report_path.exists():
            return ""
        return report_path.read_text(encoding="utf-8")

    def append_chat_message(self, slug: str, message: dict) -> None:
        idea_folder = self.create_idea_folder(slug)
        history_path = idea_folder / "chat_history.jsonl"
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False))
            handle.write("\n")

    def read_chat_history(self, slug: str) -> list[dict]:
        history_path = self.get_idea_folder(slug) / "chat_history.jsonl"
        if not history_path.exists():
            return []

        messages: list[dict] = []
        for line in history_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                messages.append(json.loads(line))
        return messages

    def _next_research_number(self, prompts_dir: Path) -> int:
        highest = 0
        if prompts_dir.exists():
            for prompt_path in prompts_dir.glob("*.md"):
                match = re.match(r"^(\d{3})-", prompt_path.name)
                if match:
                    highest = max(highest, int(match.group(1)))
        return highest + 1

    def _topic_from_filename(self, filename: str) -> str:
        stem = Path(filename).stem
        parts = stem.split("-", 1)
        return parts[1] if len(parts) > 1 else stem

    def _topic_slug(self, topic: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
        return slug or "research"

    def _safe_slug(self, slug: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-")
        return safe or "idea"
