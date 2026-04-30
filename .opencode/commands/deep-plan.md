---
description: Use premium model for architecture and task planning
agent: plan
model: codex-lb/gpt-5.5
---

Create an implementation plan for:

$ARGUMENTS

Include:
- Files to inspect (delegate to explore-cheap with SPECIFIC, SCOPED instructions — never "gather context")
- Relevant existing patterns
- Architecture impact
- Risks
- Suggested cheap subagent tasks
- Verification commands
- Unleash code-goblin on the plan before finalizing
- Clear handoff prompt for build/coder-cheap
