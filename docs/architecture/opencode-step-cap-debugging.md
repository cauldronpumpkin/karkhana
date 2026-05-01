# OpenCode step-cap debugging

## Reproduce

Run a long agent task through the repo config:

```bash
opencode run --agent build "Inspect the codebase and implement a small cross-file change"
```

If the session stops with `max number of steps reached`, capture the agent used, the provider, and whether typing `continue` resumes cleanly.

## Verify the fix

Check for the risky settings that used to cause premature shutdowns:

```bash
rg -n "maxSteps|codex-lb|timeout|doom_loop|subagent" opencode.json .opencode ~/.config/opencode
```

Suggested checks:

- build agent has a high but finite `maxSteps` budget
- plan agent has a medium `maxSteps` budget
- explore/review/goblin agents remain smaller
- codex-lb requests have provider timeout set
- no deprecated `steps` remains

## codex-lb checklist

- Sticky sessions enabled
- Usage-weighted balancing preferred
- Check logs for `429`, `400`, `413`, and stream timeout errors
- Confirm proxy restarts are not dropping long streams
- Keep API keys in environment variables only

## Notes

OpenCode’s current schema uses `maxSteps` for agent budgets. This repo keeps nested Task usage by workflow, but the higher step budgets and tighter read-only agent budgets reduce the chance of exhausting a session mid-run.
