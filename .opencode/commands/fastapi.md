---
description: Build a FastAPI endpoint with Pydantic models (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the fastapi-expert skill to implement this:

$ARGUMENTS

**Workflow:**
1. Load the `fastapi-expert` skill using the skill tool.
2. Delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find existing FastAPI routers in backend/app/routers, show me the pattern for route registration and dependency injection. Ignore frontend and tests."
3. Implement the feature following fastapi-expert skill instructions.
4. Delegate to `review-cheap` (instruct it to also load `fastapi-expert` skill) to review your work.
5. If the reviewer finds issues, fix them. If architecture concerns arise, escalate to `architect-premium`.
