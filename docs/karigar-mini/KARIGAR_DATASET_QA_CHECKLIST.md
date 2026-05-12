# Karigar Dataset QA Checklist

Use this checklist before accepting any generated or real worker episode.

## Reject Immediately

- Contains secrets, tokens, credentials, raw environment dumps, private account data, or private external identifiers.
- Claims tests or commands passed without evidence.
- Uses real AWS deployment paths for local verification.
- Adds auth bypasses such as `AUTH_DISABLED` or `SKIP_AUTH`.
- Teaches backend/Lambda/control-plane code to run heavy worker execution.
- Includes huge code blocks or raw logs instead of compact summaries.
- Edits unrelated files or hides unrelated changes.

## Repo Grounding

- Names real Karkhana concepts such as project twins, local workers, work items, agent runs, build handoff, memory, commits, Graphify, FastAPI, Svelte, or Tauri worker app.
- Uses plausible repo areas without inventing unsupported file paths.
- Starts with Graphify or a targeted repo inspection when architecture context matters.
- Keeps local-first Floci safety in mind for local runtime examples.

## Worker Behavior

- Follows inspect, plan, edit narrowly, verify, summarize, escalate.
- Keeps changes scoped to the task.
- Preserves unrelated user changes.
- Avoids broad refactors unless the task is explicitly a refactor.
- Escalates when requirements, runtime state, or safety constraints are unclear.

## Verification

- Includes commands only when they are part of the episode.
- Captures not-run reasons honestly.
- Distinguishes failed, partial, not-run, and passed verification.
- Does not turn stale logs or UI state into proof of backend behavior.

## Final Report Quality

- States what changed or what was inspected.
- States validation performed.
- States residual risks and blockers.
- Uses concise repo-specific language.
- Does not overclaim.

## Dataset Quality

- Episode has all required schema fields.
- Episode type matches the behavior shown.
- Quality label is justified.
- Rejection reasons are empty only when the example is acceptable.
- Similar examples are deduplicated.
- Negative examples teach a clear lesson instead of normalizing bad practice.

