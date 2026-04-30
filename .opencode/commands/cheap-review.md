---
description: Cheap code review using DeepSeek V4 Flash
agent: review-cheap
model: opencode-go/deepseek-v4-flash
---

Review this code or diff for issues:

$ARGUMENTS

Check for:
- Obvious bugs and logic errors
- Type errors and missing null checks
- Missing tests and coverage gaps
- Regressions and broken assumptions
- Style inconsistencies with surrounding code
- Security concerns

Return only actionable findings with file paths and line numbers.
