"""Tests for the File Manager service."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.services.file_manager import FileManager


@pytest.fixture
def fm(temp_dir: Path) -> FileManager:
    """Create a FileManager using the temp directory."""
    return FileManager(base_dir=temp_dir)


def test_create_idea_folder(fm: FileManager):
    """Happy path: create_idea_folder creates full directory tree."""
    path = fm.create_idea_folder("test-idea")
    assert path.exists()
    assert (path / "research" / "prompts").exists()
    assert (path / "research" / "results").exists()
    assert (path / "reports").exists()


def test_get_idea_folder(fm: FileManager):
    """Happy path: get_idea_folder returns correct path."""
    path = fm.get_idea_folder("my-idea")
    assert path.name == "my-idea"
    assert path.parent == fm.base_dir


def test_write_and_read_state(fm: FileManager):
    """Happy path: write_state and read_state round-trip correctly."""
    state = {"phase": "clarify", "scores": {"tam": 7.0}}
    fm.write_state("state-test", state)

    read_state = fm.read_state("state-test")
    assert read_state["phase"] == "clarify"
    assert read_state["scores"]["tam"] == 7.0


def test_read_state_nonexistent(fm: FileManager):
    """Edge case: read_state returns empty dict for nonexistent state."""
    result = fm.read_state("nonexistent-idea")
    assert result == {}


def test_save_and_read_report(fm: FileManager):
    """Happy path: write_report and read_report round-trip correctly."""
    content = "# Capture Report\n\nKey findings here."
    fm.write_report("report-test", "capture", content)

    read_content = fm.read_report("report-test", "capture")
    assert read_content == content


def test_read_report_nonexistent(fm: FileManager):
    """Edge case: read_report returns empty string for nonexistent report."""
    result = fm.read_report("nonexistent-idea", "capture")
    assert result == ""


def test_read_report_unknown_phase(fm: FileManager):
    """Edge case: read_report raises ValueError for unknown phase."""
    with pytest.raises(ValueError, match="Unknown phase"):
        fm.read_report("any-idea", "unknown_phase")


def test_write_report_unknown_phase(fm: FileManager):
    """Edge case: write_report raises ValueError for unknown phase."""
    with pytest.raises(ValueError, match="Unknown phase"):
        fm.write_report("any-idea", "unknown_phase", "content")


def test_save_research_prompt(fm: FileManager):
    """Happy path: save_research_prompt creates numbered file."""
    filename = fm.save_research_prompt("prompt-test", "Research the market", "Market Research")
    assert filename.endswith("-market-research.md")
    assert filename.startswith("001-")

    # Second prompt should be numbered 002
    filename2 = fm.save_research_prompt("prompt-test", "Research competitors", "Competitor Analysis")
    assert filename2.startswith("002-")


def test_save_and_read_chat_history(fm: FileManager):
    """Happy path: append_chat_message and read_chat_history work correctly."""
    msg1 = {"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00Z"}
    msg2 = {"role": "assistant", "content": "Hi!", "timestamp": "2024-01-01T00:01:00Z"}

    fm.append_chat_message("chat-test", msg1)
    fm.append_chat_message("chat-test", msg2)

    history = fm.read_chat_history("chat-test")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_read_chat_history_nonexistent(fm: FileManager):
    """Edge case: read_chat_history returns empty list for nonexistent history."""
    result = fm.read_chat_history("nonexistent-idea")
    assert result == []


def test_get_pending_and_completed_research(fm: FileManager):
    """Happy path: pending/completed research detection works."""
    fm.save_research_prompt("research-test", "Prompt A", "Topic A")
    fm.save_research_prompt("research-test", "Prompt B", "Topic B")

    # Upload result for first prompt only
    pending = fm.get_pending_research("research-test")
    assert len(pending) == 2  # Both pending since no results uploaded yet

    # Upload a result matching the first prompt
    fm.save_research_result("research-test", pending[0]["filename"], "Result A")

    pending = fm.get_pending_research("research-test")
    completed = fm.get_completed_research("research-test")

    assert len(pending) == 1
    assert len(completed) == 1
    assert completed[0]["topic"] == "topic-a"


def test_save_research_result(fm: FileManager):
    """Happy path: save_research_result saves file to results directory."""
    result_path = fm.save_research_result("result-test", "test-result.md", "# Results\n\nContent here.")
    assert result_path.exists()
    assert result_path.read_text(encoding="utf-8") == "# Results\n\nContent here."


def test_safe_slug_sanitization(fm: FileManager):
    """Edge case: _safe_slug sanitizes dangerous characters."""
    path = fm.get_idea_folder("idea/with\\slashes!@#")
    # Should not contain path traversal characters
    assert "/" not in path.name
    assert "\\" not in path.name
