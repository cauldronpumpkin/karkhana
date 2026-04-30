---
description: Full-stack feature — frontend + backend + security in one go (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the fullstack-guardian skill to implement this full-stack feature:

$ARGUMENTS

**Workflow:**
1. Load the `fullstack-guardian` skill using the skill tool.
2. Delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find the DB model for User, its FastAPI router, and the frontend component that displays users. Scope: backend/app/models, backend/app/routers, frontend/src/routes. Ignore tests and unrelated modules."
3. Implement end-to-end following fullstack-guardian skill instructions (database → API → UI with security at every layer).
4. Delegate to `review-cheap` (instruct it to also load `fullstack-guardian` skill) to review the full integration.
5. Delegate to `code-goblin` to stress-test for edge cases across the stack.
6. If architecture concerns arise, escalate to `architect-premium`.
