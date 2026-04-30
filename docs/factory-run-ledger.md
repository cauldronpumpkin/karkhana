# Factory Run Ledger

## Purpose

The Factory Run Ledger is a structured operational memory for each meaningful Karkhana workstream. It captures the goal, decisions, artifacts, agent handoffs, research outputs, Codex implementation results, risks, next actions, and reusable lessons.

ClickUp tracks *work state* (who is doing what, when it is due). The ledger tracks *causal memory* (why we did something, what changed, what the next agent needs, and what patterns to reuse).

## Schema

### Frontmatter: Required

| Field | Type | Description |
| --- | --- | --- |
| `run_id` | str | Stable slug and filename identity. Must match the file stem. |
| `title` | str | Human-readable workstream name. |
| `status` | str | One of: `active`, `paused`, `completed`, `cancelled`, `archived`. |
| `stage` | str | Current phase: `planning`, `research`, `implementation`, `verification`, `handoff`, `review`. |
| `created_at` | str | ISO 8601 timestamp. |
| `updated_at` | str | ISO 8601 timestamp. Updated on every mutation. |

### Frontmatter: Optional

| Field | Type | Description |
| --- | --- | --- |
| `owner_mode` | str | `human_approved_ai_assisted`, `ai_automated`, `manual`. |
| `related_clickup_tasks` | list[str] | ClickUp task IDs or URLs. |
| `related_repo_paths` | list[str] | File paths relevant to this workstream. |
| `related_graphify_communities` | list[str] | Graphify community labels (e.g. `Community 4`). |
| `related_factory_run_id` | str | Link to an existing DB-backed FactoryRun if applicable. |
| `related_project_id` | str | Link to a ProjectTwin. |
| `related_template_id` | str | Link to a TemplatePack. |
| `current_next_action` | dict | `{owner: str, action: str}` describing what should happen next. |

### Markdown Sections

Each ledger file uses consistent H2 headings so the parser can find and update them:

| Heading | Content |
| --- | --- |
| `## Current goal` | Free-text explanation of what this workstream is trying to accomplish. |
| `## Decisions` | Table: `Date`, `Decision`, `Reason`, `Made by`. |
| `## Artifacts` | Table: `Type`, `Title`, `Location`, `Status`. |
| `## Handoffs` | Table: `Date`, `From`, `To`, `Summary`, `Required output`. |
| `## Research outputs` | Table: `Source`, `Summary`, `Location`, `Integrated`. |
| `## Codex runs` | Table: `Date`, `Goal`, `Branch`, `Files changed`, `Verification`, `Result`. |
| `## Repo changes` | Bullet list of significant file/directory changes. |
| `## Verification` | Checklist of verification steps and their pass/fail state. |
| `## Open questions` | Bullet list of unresolved questions. |
| `## Risks` | Bullet list of known risks and mitigations. |
| `## Next actions` | Table: `Owner`, `Action`, `Priority`. |
| `## Reusable lessons` | Bullet list of patterns and insights for future work. |

All table sections use the standard pipe-table format with a header separator row (`|---|---|---|`).

## How to Use

### Manual rule

After every meaningful handoff, update the ledger with:

- **what changed** — describe the delta in repo, artifacts, or understanding.
- **why it changed** — the decision and reasoning.
- **what artifact was produced** — link to files, commits, or documents.
- **what verification ran** — test commands, lint runs, Graphify updates.
- **what the next agent should know** — context for the next handoff receiver.

### Agent roles

| Agent | Responsible for |
| --- | --- |
| Human | Sets goals, reviews, approves scope, updates ClickUp tasks. |
| ChatGPT | Planning: writes goals, decisions, handoffs, research prompts. |
| Gemini / deep research | Research outputs: populates `## Research outputs`. |
| Codex | Implementation: populates `## Codex runs`, `## Repo changes`, `## Verification`, `## Risks`, `## Next actions`. |
| Future Karkhana automation | Auto-append entries from FactoryRun/WorkerEvent/ProjectMemory events. |

## How Workers Use Ledgers

Workers treat the ledger as the durable handoff record for a factory run. After meaningful implementation work, a worker should update the run ledger when it exists and report whether that happened in its result payload.

Policies:

- Update the ledger only for meaningful changes, decisions, verification, risks, next actions, or reusable lessons.
- Prefer `## Codex runs`, `## Repo changes`, `## Verification`, `## Risks`, `## Next actions`, and `## Reusable lessons` for worker updates.
- Keep entries factual and concise; do not invent verification results, commit SHAs, or follow-up work.
- If verification was not run or a value is unknown, record `not run`, `pending`, or explain the uncertainty.
- Set `ledger_updated` to `true` only when the worker actually changed the ledger.
- Set `ledger_sections_updated` to the exact H2 section names touched; use an empty array when no ledger was updated.

Worker result payload example:

```json
{
  "summary": "Added backend validation for the assigned factory phase.",
  "files_modified": ["backend/app/services/example.py"],
  "tests_passed": true,
  "test_output": "python -m pytest backend/tests/test_example.py passed",
  "graphify_updated": true,
  "ledger_updated": true,
  "ledger_sections_updated": ["## Codex runs", "## Repo changes", "## Verification"],
  "branch_name": "factory/run_123/backend",
  "phase_artifacts": {}
}
```

## Parser / Service

The `FactoryRunLedgerService` in `backend/app/services/factory_run_ledger.py` provides:

- `read_ledger(run_id)` — parse frontmatter and return structured metadata + body.
- `create_ledger(run_id, title)` — create a new ledger file from scratch.
- `append_decision`, `append_artifact`, `append_handoff`, `append_codex_run` — append rows to table sections.
- `append_risk`, `append_next_action`, `append_reusable_lesson` — append bullets to list sections.
- Internal YAML parser supports the frontmatter forms used in these ledgers (scalars, quoted strings, inline lists, block lists, shallow dicts).

### Future endpoint design

When a read/write API is warranted, the following endpoints would match the existing router pattern in `backend/app/routers/factory_runs.py`:

```
GET    /api/factory-run-ledgers                    → list all ledgers
GET    /api/factory-run-ledgers/{run_id}           → read single ledger
POST   /api/factory-run-ledgers                    → create ledger
POST   /api/factory-run-ledgers/{run_id}/entries   → append entry
```

The service design already supports these operations directly.

## Future Automation

The ledger design intentionally maps to these future Karkhana capabilities:

| Capability | How the ledger feeds it |
| --- | --- |
| Database-backed entity | Frontmatter fields map to a `FactoryRunLedger` dataclass or DDB item; markdown body stored in S3. |
| ClickUp-linked tracker | `related_clickup_tasks` field links ledgers to tasks; a webhook can sync status. |
| Worker-run event log | `WorkerEvent` records can auto-append Codex run rows. |
| Template-learning source | `## Reusable lessons` sections feed `TemplateMemory` and template update proposals. |
| Prompt/context bundle | Ledger body + frontmatter can be read and included in Codex system prompts. |
| Graphify-indexed causal memory | Graphify indexes ledger files and their relationships to code, services, and other artifacts. |
| Orchestrator feed | `current_next_action` tells Karkhana what to do next without human parsing. |

## Evolution Path

1. **MVP (this slice):** Repo-native markdown + standalone service + tests. No API.
2. **Phase 2:** API endpoints for read/write. Frontend can list and display ledgers.
3. **Phase 3:** Auto-append from FactoryRun/WorkerEvent events. Automation reduces manual editing.
4. **Phase 4:** ClickUp integration — ledger entries create/update ClickUp checklists and vice versa.
5. **Phase 5:** Template learning — reusable lessons auto-propose TemplateMemory and TemplateUpdateProposal entries.
