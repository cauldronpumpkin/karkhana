---
description: Security audit — find vulnerabilities and produce remediation report (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the security-reviewer skill to conduct a security audit on:

$ARGUMENTS

**Workflow:**
1. Load the `security-reviewer` skill using the skill tool.
2. Delegate to `review-cheap` with instructions to also load `security-reviewer` skill and perform a thorough security review.
3. After the review, delegate to `code-goblin` to adversarially stress-test the findings.
4. Compile a final report with severity ratings and actionable remediation.
5. If critical vulnerabilities are found, escalate to `architect-premium` for architectural remediation guidance.
