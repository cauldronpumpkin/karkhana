---
description: Fix a small bug using GPT-5.4 Mini
agent: build
model: codex-lb/gpt-5.4-mini
---

Fix this issue using GPT-5.4 Mini (code writing only).

Rules:
- First delegate to "explore-cheap" with SPECIFIC instructions — tell it exactly what files, symbols, or patterns to look for. Do NOT say "gather context".
- Prefer minimal edits.
- Do not redesign architecture.
- Run targeted tests if available.
- After fixing, delegate to "review-cheap" to verify the fix.
- If something feels off or edge-casey, unleash "code-goblin" on it.
- If the issue seems architectural, ambiguous, security-sensitive, or still failing after reasonable attempts, escalate to "architect-premium" or "staff-engineer".

Task:
$ARGUMENTS
