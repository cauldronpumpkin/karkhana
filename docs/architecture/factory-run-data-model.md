# Karkhana Factory Run Data Model

## Overview

The Factory Run data model governs how Karkhana executes template-driven builds.
A **FactoryRun** orchestrates one or more **FactoryPhase** records, each containing
**FactoryBatch** records that map to discrete work items executed by OpenCode local
workers. Every batch can have one or more **VerificationRun** records for test/lint
gate checks.

Templates provide the blueprints. A **TemplatePack** declares phases, quality gates,
default stack, constraints, and worker configuration. **TemplateArtifact** records
store individual file-level content or URIs (prompts, configs, scaffolding files).

## Entity Relationships

```
TemplatePack (1) ──── (N) TemplateArtifact
TemplatePack (1) ──── (N) TemplateManifest
TemplatePack (1) ──── (N) TemplateMemory
TemplatePack (1) ──── (N) TemplateUpdateProposal

FactoryRun (1) ──── (N) FactoryPhase
FactoryRun (1) ──── TemplatePack  (via template_id)
FactoryRun (1) ──── Idea          (via idea_id)

FactoryPhase (1) ──── (N) FactoryBatch
FactoryBatch (1) ──── (N) VerificationRun
FactoryBatch (1) ──── WorkItem    (optional, via work_item_id)
```

## Entity Definitions

### TemplatePack
Top-level template definition. Declares the phases, quality gates, stack defaults,
constraints, and worker config for a category of builds.

| Field | Type | Notes |
|-------|------|-------|
| template_id | str | Natural key (e.g. "fullstack-saas-v1") |
| version | str | Semver (e.g. "1.0.0") |
| channel | str | "stable" / "beta" / "experimental" |
| display_name | str | Human-readable name |
| description | str | What this template produces |
| phases | list[dict] | Ordered phase definitions |
| quality_gates | list[dict] | Pass/fail criteria between phases |
| default_stack | dict | Default tech stack choices |
| constraints | list[dict] | Hard limits (timeout, cost, etc.) |
| opencode_worker | dict | Worker engine config |

### TemplateArtifact
Individual file or content blob belonging to a template. Large content is stored
in S3 and referenced by `uri`; small content can be inline.

| Field | Type | Notes |
|-------|------|-------|
| template_id | str | FK to TemplatePack |
| artifact_key | str | e.g. "prompts/project_setup.md" |
| content_type | str | MIME type |
| uri | str | S3 URI or inline content reference |
| content | str | Inline content (small artifacts only) |
| metadata_ | dict | Arbitrary metadata |

### FactoryRun
A single execution of a template against an idea. The primary coordination record.

| Field | Type | Notes |
|-------|------|-------|
| idea_id | str | FK to Idea |
| template_id | str | FK to TemplatePack |
| status | str | queued / running / completed / failed |
| config | dict | Run-level config overrides |
| tracking_manifest_uri | str | S3 URI for large tracking manifest |
| completed_at | datetime | Set when run finishes |

### FactoryPhase
One phase within a factory run (e.g. "project_setup", "backend", "testing").

| Field | Type | Notes |
|-------|------|-------|
| factory_run_id | str | FK to FactoryRun |
| phase_key | str | Matches TemplatePack phase key |
| phase_order | int | Execution order (1-based) |
| status | str | pending / running / completed / failed / skipped |
| config_override | dict | Phase-specific overrides |
| output_uri | str | S3 URI for phase output artifacts |

### FactoryBatch
A discrete unit of work within a phase, typically mapping to one WorkItem.

| Field | Type | Notes |
|-------|------|-------|
| factory_phase_id | str | FK to FactoryPhase |
| factory_run_id | str | FK to FactoryRun (denormalized for query) |
| batch_key | str | e.g. "backend-api", "frontend-components" |
| status | str | pending / running / completed / failed |
| worker_id | str | Assigned local worker |
| work_item_id | str | FK to WorkItem (optional) |
| input_uri | str | S3 URI for batch input |
| output_uri | str | S3 URI for batch output |

### VerificationRun
A verification gate for a batch (test suite, lint, typecheck, code review).

| Field | Type | Notes |
|-------|------|-------|
| factory_batch_id | str | FK to FactoryBatch |
| factory_run_id | str | FK to FactoryRun (denormalized) |
| verification_type | str | test / lint / typecheck / review |
| status | str | pending / running / passed / failed / error |
| result_uri | str | S3 URI for full verification output |
| result_summary | str | Short pass/fail summary |

### TemplateManifest
Snapshot of which artifacts compose a template at a given version.

### TemplateMemory
Per-template learned knowledge (what works, what doesn't).

### TemplateUpdateProposal
Proposed change to a template, pending review.

### FactoryRunTrackingManifest (Document)
Not a DDB entity itself, but a JSON document stored in S3 and referenced by
`FactoryRun.tracking_manifest_uri`. Contains the full run state including
all phases, batches, verification results, and timing data.

## DynamoDB vs S3/Reference Split

### What goes in DynamoDB
- All entity metadata (ids, status, timestamps, small config dicts)
- Fields needed for querying, filtering, and status transitions
- Keeps items under 400KB DDB item limit

### What goes in S3 (referenced by URI)
- Large template artifact content (prompts, configs, scaffolding files)
- Factory run tracking manifests (growing documents)
- Verification run full output (test logs, coverage reports)
- Batch input/output artifacts (code diffs, generated files)

### Rationale
- DynamoDB provides fast, queryable status tracking for orchestration
- S3 provides cheap, unlimited storage for large artifacts
- URIs in DDB fields maintain the link without bloating items
- Pay-per-request billing on both services keeps costs proportional to usage
- Workers fetch artifact content from S3, not from the API

## DynamoDB Key Schema

All entities use the same single-table design with PK/SK + GSI1/GSI2:

| Entity | PK | SK | GSI1PK | GSI1SK | GSI2PK | GSI2SK |
|--------|----|----|--------|--------|--------|--------|
| TemplatePack | `TEMPLATE#{id}` | `PACK#METADATA` | `TEMPLATE_PACKS` | `{ts}#{id}` | - | - |
| TemplateArtifact | `TEMPLATE#{id}` | `ARTIFACT#{key}` | - | - | - | - |
| TemplateManifest | `TEMPLATE#{id}` | `MANIFEST#{ver}` | - | - | - | - |
| TemplateMemory | `TEMPLATE#{id}` | `TMEM#{cat}#{key}` | - | - | - | - |
| TemplateUpdateProposal | `TEMPLATE#{id}` | `TProposal#{id}` | `T_PROPOSALS` | `{status}#{ts}#{id}` | - | - |
| FactoryRun | `FACTORY_RUN#{id}` | `METADATA` | `IDEA#{idea_id}` | `FRUN#{ts}#{id}` | `TEMPLATE#{tid}` | `FRUN#{ts}#{id}` |
| FactoryPhase | `FACTORY_RUN#{run_id}` | `PHASE#{order:03d}#{key}` | - | - | `FRUN#{run_id}` | `PHASE#{order:03d}` |
| FactoryBatch | `FACTORY_RUN#{run_id}` | `BATCH#{phase_id}#{key}` | - | - | `FPHASE#{phase_id}` | `BATCH#{key}` |
| VerificationRun | `FACTORY_RUN#{run_id}` | `VERIFY#{batch_id}#{type}` | - | - | `FBATCH#{batch_id}` | `VERIFY#{type}` |

## Factory Run Lifecycle

```
1. User selects TemplatePack + Idea → FactoryRun created (status: queued)
2. FactoryRun transitions to running
3. For each phase (in order):
   a. FactoryPhase created (status: pending → running)
   b. For each batch in phase:
      - FactoryBatch created (status: pending)
      - WorkItem enqueued for local worker
      - Batch status: pending → running
      - Worker completes → batch status: completed/failed
   c. VerificationRuns created for completed batches
   d. Phase status: completed/failed
4. All phases done → FactoryRun status: completed/failed
5. FactoryRunTrackingManifest generated and uploaded to S3
```

## Existing Entity Compatibility

This data model is **additive only**. No existing entities (Idea, ProjectTwin,
WorkItem, AgentRun, ProjectCommit, LocalWorker, etc.) are modified. FactoryRun
references existing entities via foreign keys but does not alter their schemas.
