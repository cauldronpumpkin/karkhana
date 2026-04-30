---
run_id: factory-run-ledger
title: Factory Run Ledger MVP
status: active
stage: implementation
owner_mode: human_approved_ai_assisted
created_at: "2026-04-30T00:00:00Z"
updated_at: "2026-04-30T00:00:00Z"
related_clickup_tasks: []
related_repo_paths:
  - karkhana-runs/factory-run-ledger.md
  - docs/factory-run-ledger.md
  - backend/app/services/factory_run_ledger.py
  - backend/tests/test_factory_run_ledger.py
related_graphify_communities:
  - Community 4
  - Community 5
  - Community 9
current_next_action:
  owner: codex
  action: Implement first repo-native Factory Run Ledger MVP
---

# Factory Run Ledger MVP

## Current goal

Create a structured ledger for Karkhana workstreams so manual AI/human/tool coordination can later become automated orchestration. The ledger captures goal, decisions, artifacts, handoffs, research outputs, Codex implementation results, risks, next actions, and reusable lessons.

## Decisions

| Date | Decision | Reason | Made by |
| --- | --- | --- | --- |
| 2026-04-30 | Use repo-native markdown ledgers as first artifact | Codex and Graphify can read them immediately; no DB migration required | Human + ChatGPT |
| 2026-04-30 | Skip API endpoint in MVP slice | Keeping scope small avoids auth/route/frontend integration questions | Human + Codex |
| 2026-04-30 | Build standalone service not coupled to existing FactoryRunService | Ledger is repo-native markdown; existing service is DB-bound orchestration | Codex |

## Artifacts

| Type | Title | Location | Status |
| --- | --- | --- | --- |
| doc | Factory Run Ledger schema | docs/factory-run-ledger.md | active |
| ledger | This ledger | karkhana-runs/factory-run-ledger.md | active |
| service | FactoryRunLedgerService | backend/app/services/factory_run_ledger.py | pending |
| test | Ledger parser/appender tests | backend/tests/test_factory_run_ledger.py | pending |

## Handoffs

| Date | From | To | Summary | Required output |
| --- | --- | --- | --- | --- |
| 2026-04-30 | Human + ChatGPT | Codex | Implement first Factory Run Ledger MVP | files changed, tests passing, docs written, Graphify index updated |

## Research outputs

| Source | Summary | Location | Integrated |
| --- | --- | --- | --- |
| Graphify | GRAPH_REPORT.md shows FactoryRunService, FactoryRunTrackingManifest, WorkerEvent, MemoryService, FileManager as central nodes | graphify-out/GRAPH_REPORT.md | true |

## Codex runs

| Date | Goal | Branch | Files changed | Verification | Result |
| --- | --- | --- | --- | --- | --- |
| 2026-04-30 | Implement Factory Run Ledger MVP | main | karkhana-runs/factory-run-ledger.md, docs/factory-run-ledger.md, backend/app/services/factory_run_ledger.py, backend/tests/test_factory_run_ledger.py, karkhana-runs/.gitkeep | python -m pytest backend/tests/test_factory_run_ledger.py + graphify update . | pending |

## Repo changes

- Created `karkhana-runs/` directory with `.gitkeep` and initial ledger
- Added `docs/factory-run-ledger.md` with schema, usage, and future automation notes
- Added `backend/app/services/factory_run_ledger.py` with parser, validator, and append methods
- Added `backend/tests/test_factory_run_ledger.py` with four coverage tests

## Verification

- [ ] pytest ledger tests pass
- [ ] Graphify update succeeds
- [ ] Human can read and manually edit the ledger

## Open questions

- Should ledger entries be automatically promoted into reusable product memory (TemplateMemory, ProjectMemory)?
- Which ledger fields should become database-backed later for querying across runs?
- Should a future API provide read/write access for the frontend and workers?

## Risks

- Ledger could become stale if not updated after each meaningful handoff; manual discipline is required until automation exists.
- Too much structure could discourage manual use during fast-paced work.
- Custom YAML parser is scoped to MVP frontmatter forms; richer YAML will require adding a real parser dependency.

## Next actions

| Owner | Action | Priority |
| --- | --- | --- |
| Codex | Implement FactoryRunLedgerService with parse, create, append methods | High |
| Codex | Write focused tests for parse, validation, append, and content preservation | High |
| Human | Review and manually update ledger after next ChatGPT planning session | Medium |
| Graphify | Index new artifacts into knowledge graph | Medium |

## Reusable lessons

- Every major workstream needs causal memory, not just task status. ClickUp tracks work; the ledger tracks why, artifacts, handoffs, and what the next agent needs.
- Starting repo-native avoids infrastructure decisions and lets content drive later automation design.
- Graphify community analysis helped identify which existing services to integrate with (Community 4 = orchestration, Community 5 = tracking, Community 9 = factory run data model).
