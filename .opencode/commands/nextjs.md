---
description: Build a Next.js 14+ feature with App Router (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the nextjs-developer skill to implement this:

$ARGUMENTS

**Workflow:**
1. Load the `nextjs-developer` skill using the skill tool.
2. Delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find existing Next.js App Router pages in the frontend, show me the layout structure and API route patterns. Ignore backend tests."
3. Implement the feature following nextjs-developer skill instructions.
4. Delegate to `review-cheap` (instruct it to also load `nextjs-developer` skill) to review your work.
5. If the reviewer finds issues, fix them. If architecture concerns arise, escalate to `architect-premium`.
