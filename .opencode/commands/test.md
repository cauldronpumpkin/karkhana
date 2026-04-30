---
description: Write tests with proper strategy, mocking, coverage (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the test-master skill to implement tests for:

$ARGUMENTS

**Workflow:**
1. Load the `test-master` skill using the skill tool.
2. Delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find the test directory structure, pytest config, and existing tests for the module I'm working on. Ignore unrelated modules."
3. Write comprehensive tests following test-master skill instructions.
4. Run the tests to verify they pass.
5. Delegate to `review-cheap` (instruct it to also load `test-master` skill) to review test quality.
