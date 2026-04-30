---
description: Write Python code with type safety, async, tests (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the python-pro skill to implement this:

$ARGUMENTS

**Workflow:**
1. Load the `python-pro` skill using the skill tool.
2. Delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find the Python module structure, pyproject.toml location, and test setup for the package I'm working on. Ignore unrelated packages."
3. Implement the feature following python-pro skill instructions (type hints, proper error handling, tests).
4. Delegate to `review-cheap` (instruct it to also load `python-pro` skill) to review your work.
5. If the reviewer finds issues, fix them. If architecture concerns arise, escalate to `architect-premium`.
