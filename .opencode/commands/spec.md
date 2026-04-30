---
description: Define a new feature with requirements, user stories, acceptance criteria (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the feature-forge skill to define this feature:

$ARGUMENTS

**Workflow:**
1. Load the `feature-forge` skill using the skill tool.
2. Delegate to `architect-premium` with instructions to also load `feature-forge` skill.
3. The architect will run a structured requirements workshop.
4. Delegate to `code-goblin` to adversarially challenge assumptions and find missing requirements.
5. Produce: user stories, EARS-format requirements, acceptance criteria, and implementation checklist.

**Note**: This is a planning/specification task. No files should be edited.
