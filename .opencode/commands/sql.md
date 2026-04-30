---
description: Optimize SQL queries or design database schemas (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the sql-pro skill for this database task:

$ARGUMENTS

**Workflow:**
1. Load the `sql-pro` skill using the skill tool.
2. If the task involves understanding existing queries, delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find all SQL queries involving the orders table and related migrations. Ignore unrelated tables."
3. Implement the query optimization or schema design following sql-pro skill instructions.
4. Run EXPLAIN/ANALYZE if possible to verify improvements.
5. Delegate to `review-cheap` (instruct it to also load `sql-pro` skill) to review the changes.
6. If the issue involves deep database engine problems, escalate to `staff-engineer`.
