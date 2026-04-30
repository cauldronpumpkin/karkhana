"""Tests for the Factory Run Ledger service."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.services.factory_run_ledger import (
    FactoryRunLedgerError,
    FactoryRunLedgerService,
    _append_bullet,
    _append_table_row,
    _format_frontmatter,
    _parse_frontmatter,
    _validate_required,
    extract_compact_ledger_context,
    resolve_repo_relative_ledger_path,
    validate_ledger_metadata,
    validate_ledger_policy,
)

VALID_LEDGER = """---
run_id: test-run
title: Test Run
status: active
stage: implementation
created_at: "2026-04-30T00:00:00Z"
updated_at: "2026-04-30T00:00:00Z"
---

# Test Run

## Current goal

Test the ledger parser.

## Decisions

| Date | Decision | Reason | Made by |
| --- | --- | --- | --- |
| 2026-04-30 | Use markdown | Works for MVP | Human |

## Risks

- Risk one
- Risk two
"""


@pytest.fixture
def service(temp_dir: Path) -> FactoryRunLedgerService:
    return FactoryRunLedgerService(base_dir=temp_dir)


# ---------- parse ----------

def test_parse_valid_ledger() -> None:
    result = FactoryRunLedgerService().parse_text(VALID_LEDGER)
    assert result["run_id"] == "test-run"
    assert result["title"] == "Test Run"
    assert result["status"] == "active"
    assert result["stage"] == "implementation"
    assert result["created_at"] == "2026-04-30T00:00:00Z"
    assert result["updated_at"] == "2026-04-30T00:00:00Z"
    assert "Test the ledger parser" in result["body"]


def test_reject_missing_required_frontmatter() -> None:
    for field in ["run_id", "title", "status", "stage", "created_at", "updated_at"]:
        text = VALID_LEDGER.replace(field, "removed_field_xyz")
        with pytest.raises(FactoryRunLedgerError, match="Missing required frontmatter"):
            FactoryRunLedgerService().parse_text(text)


def test_parse_invalid_no_frontmatter() -> None:
    with pytest.raises(FactoryRunLedgerError, match="Missing frontmatter delimiter"):
        FactoryRunLedgerService().parse_text("# Just a heading\n")


def test_parse_invalid_unclosed_frontmatter() -> None:
    with pytest.raises(FactoryRunLedgerError, match="Unclosed frontmatter delimiter"):
        FactoryRunLedgerService().parse_text("---\nrun_id: broken\n")


def test_validate_ledger_policy() -> None:
    assert validate_ledger_policy(None) == "none"
    assert validate_ledger_policy("read_only") == "read_only"
    assert validate_ledger_policy(" REQUIRED ") == "required"
    with pytest.raises(FactoryRunLedgerError, match="Invalid ledger_policy"):
        validate_ledger_policy("sometimes")


def test_validate_ledger_metadata_requires_path_for_required_policy() -> None:
    assert validate_ledger_metadata({"ledger_policy": "none"}) == {
        "ledger_policy": "none",
        "ledger_path": None,
    }
    assert validate_ledger_metadata({"ledger_policy": "strict", "ledger_path": "karkhana-runs/run.md"}) == {
        "ledger_policy": "strict",
        "ledger_path": "karkhana-runs/run.md",
    }
    with pytest.raises(FactoryRunLedgerError, match="ledger_path is required"):
        validate_ledger_metadata({"ledger_policy": "required"})


def test_resolve_repo_relative_ledger_path_rejects_escape() -> None:
    assert resolve_repo_relative_ledger_path("./karkhana-runs\\run.md") == "karkhana-runs/run.md"
    with pytest.raises(FactoryRunLedgerError, match="traversal"):
        resolve_repo_relative_ledger_path("../run.md")


def test_extract_compact_ledger_context(service: FactoryRunLedgerService, temp_dir: Path) -> None:
    path = service.create_ledger("compact-test", "Compact Test")
    context = extract_compact_ledger_context(path.name, repo_root=temp_dir, max_chars=20)
    assert context["ledger_path"] == "compact-test.md"
    assert context["available"] is True
    assert context["run_id"] == "compact-test"
    assert context["title"] == "Compact Test"
    assert "sections" in context


# ---------- create ----------

def test_create_ledger(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("my-run", "My First Run")
    assert path.exists()
    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert result["run_id"] == "my-run"
    assert result["title"] == "My First Run"
    assert result["status"] == "active"
    assert result["stage"] == "planning"


def test_create_ledger_already_exists(service: FactoryRunLedgerService) -> None:
    service.create_ledger("dup-run", "First")
    with pytest.raises(FactoryRunLedgerError, match="already exists"):
        service.create_ledger("dup-run", "Second")


# ---------- read ----------

def test_read_ledger_nonexistent(service: FactoryRunLedgerService) -> None:
    with pytest.raises(FactoryRunLedgerError, match="Ledger not found"):
        service.read_ledger("nonexistent-run")


def test_compact_context_includes_key_sections_without_full_body(service: FactoryRunLedgerService) -> None:
    giant_body = "GIANT_FULL_BODY_SENTINEL " * 500
    path = service.create_ledger("compact-test", "Compact Test")
    path.write_text(
        """---
run_id: compact-test
title: Compact Test
status: active
stage: implementation
created_at: "2026-04-30T00:00:00Z"
updated_at: "2026-04-30T00:00:00Z"
owner: factory
---

# Compact Test

Intro that should not be copied wholesale.

## Current goal

Ship ledger-aware workers.

## Decisions

| Date | Decision | Reason | Made by |
| --- | --- | --- | --- |
| 2026-04-30 | Require updates | Durable handoffs | team |

## Risks

- Workers may forget updates.

## Next actions

| Owner | Action | Priority |
| --- | --- | --- |
| Codex | Add tests | High |

## Artifacts

| Type | Title | Location | Status |
| --- | --- | --- | --- |
| test | Ledger tests | backend/tests | active |

## Reusable lessons

- Keep context compact.

## Full research dump

""" + giant_body,
        encoding="utf-8",
    )

    context = service.compact_context(path)

    assert context["frontmatter"]["run_id"] == "compact-test"
    sections = context["sections"]
    assert "Ship ledger-aware workers" in sections["Current goal"]
    assert "Require updates" in sections["Decisions"]
    assert "Workers may forget updates" in sections["Risks"]
    assert "Add tests" in sections["Next actions"]
    assert "Ledger tests" in sections["Artifacts"]
    assert "Keep context compact" in sections["Reusable lessons"]
    assert giant_body.strip() not in str(context)


# ---------- append decision (table) ----------

def test_append_decision_preserves_markdown(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("decision-test", "Decision Test", stage="planning")
    text = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(text)
    body = _append_table_row(body, "Decisions", ["2026-04-30", "Use markdown", "Works for MVP", "Human"])
    _write_and_reload(path, metadata, body)

    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "2026-04-30" in result["body"]
    assert "Use markdown" in result["body"]
    assert "Works for MVP" in result["body"]
    assert "Human" in result["body"]


def test_append_decision_creates_table_if_missing(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("no-decision-table", "No Table")
    service.append_decision(path.stem, date="2026-04-30", decision="Test", reason="Testing", made_by="Codex")
    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "## Decisions" in result["body"]
    assert "Test" in result["body"]


# ---------- append risk (bullet) ----------

def test_append_risk_preserves_content(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("risk-test", "Risk Test", stage="planning")
    text = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(text)
    body = _append_bullet(body, "Risks", "Ledger could become stale")
    _write_and_reload(path, metadata, body)

    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "Ledger could become stale" in result["body"]


def test_append_risk_creates_section_if_missing(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("no-risk-section", "No Risks")
    text = path.read_text(encoding="utf-8")
    assert "## Risks" not in text

    body_updated = _append_bullet(text.split("---", 2)[2].strip(), "Risks", "New risk")
    metadata, _ = _parse_frontmatter(text)
    _write_and_reload(path, metadata, body_updated)

    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "## Risks" in result["body"]
    assert "New risk" in result["body"]


# ---------- append reusable lesson (bullet) ----------

def test_append_reusable_lesson(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("lesson-test", "Lesson Test")
    service.append_reusable_lesson(path.stem, "Causal memory is valuable")
    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "Causal memory is valuable" in result["body"]


# ---------- append handoff ----------

def test_append_handoff(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("handoff-test", "Handoff Test")
    service.append_handoff(
        path.stem,
        date="2026-04-30",
        from_="ChatGPT",
        to="Codex",
        summary="Implement the MVP",
        required_output="files changed, tests run",
    )
    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "ChatGPT" in result["body"]
    assert "Codex" in result["body"]
    assert "Implement the MVP" in result["body"]


# ---------- append next action (table) ----------

def test_append_next_action(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("action-test", "Action Test")
    service.append_next_action(path.stem, owner="Codex", action="Write tests", priority="High")
    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "Codex" in result["body"]
    assert "Write tests" in result["body"]
    assert "High" in result["body"]


# ---------- append artifact (table) ----------

def test_append_artifact(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("artifact-test", "Artifact Test")
    service.append_artifact(path.stem, artifact_type="doc", title="Schema", location="docs/", status="active")
    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "doc" in result["body"]
    assert "Schema" in result["body"]


# ---------- append codex run (table) ----------

def test_append_codex_run(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("codex-test", "Codex Run Test")
    service.append_codex_run(
        path.stem,
        date="2026-04-30",
        goal="Implement MVP",
        branch="main",
        files_changed="src/foo.py",
        verification="pytest",
        result="passed",
    )
    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert "Implement MVP" in result["body"]
    assert "main" in result["body"]
    assert "passed" in result["body"]


# ---------- multiple appends ----------

def test_append_multiple_decisions(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("multi-decision", "Multi Decision")
    for i in range(3):
        service.append_decision(path.stem, date=f"2026-04-{30-i}", decision=f"Decision {i}", reason=f"Reason {i}", made_by="Codex")
    result = service.parse_text(path.read_text(encoding="utf-8"))
    for i in range(3):
        assert f"Decision {i}" in result["body"]
    lines = result["body"].split("\n")
    decision_lines = [l for l in lines if l.strip().startswith("| 2026-04-")]
    assert len(decision_lines) == 3


# ---------- body content preservation ----------

def test_body_content_preserved_across_appends(service: FactoryRunLedgerService) -> None:
    path = service.create_ledger("content-test", "Content Test")
    secret = "UNIQUE_CONTENT_STRING_THAT_MUST_SURVIVE"
    text = path.read_text(encoding="utf-8")
    text = text.replace("## Current goal\n", f"## Current goal\n\n{secret}\n")
    path.write_text(text, encoding="utf-8")

    service.append_risk(path.stem, "Some risk")
    service.append_decision(path.stem, date="2026-04-30", decision="Keep content", reason="Preservation test", made_by="Codex")

    result = service.parse_text(path.read_text(encoding="utf-8"))
    assert secret in result["body"]
    assert "Some risk" in result["body"]
    assert "Keep content" in result["body"]


# ---------- helpers ----------

def _write_and_reload(path: Path, metadata: dict, body: str) -> None:
    from backend.app.services.factory_run_ledger import _write_ledger
    _write_ledger(path, metadata, body)


# ---------- yaml roundtrip ----------

def test_frontmatter_roundtrip() -> None:
    metadata = {
        "run_id": "rt-test",
        "title": "Roundtrip",
        "status": "active",
        "stage": "planning",
        "created_at": "2026-04-30T00:00:00Z",
        "updated_at": "2026-04-30T00:00:00Z",
        "related_repo_paths": ["a.md", "b.py"],
        "related_clickup_tasks": [],
    }
    fm = _format_frontmatter(metadata)
    parsed, _ = _parse_frontmatter(fm + "\n\n# Body\n")
    assert parsed["run_id"] == "rt-test"
    assert parsed["title"] == "Roundtrip"
    assert parsed["related_repo_paths"] == ["a.md", "b.py"]
    assert parsed["related_clickup_tasks"] == []
