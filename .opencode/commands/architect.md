---
description: Design system architecture or make architectural decisions (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the architecture-designer skill to address this architectural concern:

$ARGUMENTS

**Workflow:**
1. Load the `architecture-designer` skill using the skill tool.
2. Delegate to `architect-premium` with instructions to also load `architecture-designer` skill.
3. The architect will use `explore-cheap` with SPECIFIC, SCOPED instructions — e.g., "Find the service layer patterns in backend/app/services and how they interact with repositories. Ignore frontend and tests."
4. The architect will use `code-goblin` to adversarially stress-test architectural decisions.
5. Receive: architecture diagrams, ADRs, trade-off analysis, and handoff instructions.
6. If implementation is needed after the architectural decision, create a plan and execute with appropriate skill-loaded coder-cheap subagent.

**Note**: This is a planning task. No files should be edited during the architecture phase.
