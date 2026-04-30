---
description: Debug a hard error — trace, diagnose, fix (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the debugging-wizard skill to debug this issue:

$ARGUMENTS

**Workflow:**
1. Load the `debugging-wizard` skill using the skill tool.
2. Delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find the error handler for XException in backend/app, show me the stack trace handling and related log config. Ignore frontend and tests."
3. Apply the debugging-wizard's systematic hypothesis-driven methodology to isolate root cause.
4. Fix the issue with minimal targeted edits.
5. Delegate to `review-cheap` (instruct it to also load `debugging-wizard` skill) to verify the fix.
6. If the issue is genuinely hard (race condition, memory corruption, distributed failure), escalate to `staff-engineer`.
