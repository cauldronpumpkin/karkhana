# Dataset Generation Prompts

These prompts create candidate Karigar-Mini episodes. All outputs must be reviewed, scrubbed, deduplicated, and validated before acceptance.

## Generate Realistic Karkhana Worker Tasks

```text
You are generating candidate tasks for Karigar-Mini, a local coding worker for the Karkhana / Idea Refinery repo.

Use these concepts: project twins, local workers, work items, agent runs, commits, Graphify, memory, build handoff, FastAPI backend, Svelte frontend, Tauri worker app, local-first Floci runtime.

Return JSON only:
{
  "tasks": [
    {
      "title": "...",
      "episode_type": "worker_execution_success|worker_execution_failure|cloud_rescue|repo_inspection_plan|test_failure_triage|architecture_guardrail_review|final_worker_report|escalation_decision",
      "user_request": "...",
      "repo_areas": ["..."],
      "constraints": ["..."],
      "expected_worker_behavior": ["..."],
      "quality_risks": ["..."]
    }
  ]
}

Create 10 tasks. Keep them repo-specific but do not include secrets, exact private account data, or large code blocks.
```

## Generate Ideal Worker Execution Traces

```text
You are creating ideal supervised fine-tuning examples for Karigar-Mini.

Given the task below, produce one JSON object conforming to the Karigar Worker Episode schema. The trace must teach: inspect repo context, plan narrowly, edit only scoped files, verify honestly, summarize results, and escalate if needed.

Task:
{{TASK_JSON}}

Rules:
- Do not invent exact command success unless the task says it happened.
- Do not include secrets or raw environment variables.
- Keep patches as summaries, not large code blocks.
- Mention Graphify-first inspection when architecture or codebase context matters.
- Use Karkhana concepts accurately.

Return one JSON object only.
```

## Generate Failed Local Attempts

```text
Create a realistic failed local Karigar worker episode for the Idea Refinery repo.

The failure should be useful training data, not sloppy behavior. The worker should inspect relevant context, avoid unsafe changes, try reasonable verification, capture failure evidence, and report honestly.

Return one JSON object conforming to the Karigar Worker Episode schema.

Required:
- episode_type must be "worker_execution_failure" or "test_failure_triage".
- quality_label should be "accept" only if the failure is honest and educational.
- Include an escalation_reason when cloud rescue or human input is needed.
- Do not include secrets, credentials, or large logs.
```

## Generate Cloud Rescue Traces

```text
Create a cloud_rescue episode for Karigar-Mini.

Input failed attempt:
{{FAILED_EPISODE_JSON}}

Produce one corrected rescue trace that shows what a stronger cloud teacher would do next. Preserve the original failure as context, identify the missing inspection or verification step, and propose a safe recovery. Keep changes narrow and repo-specific.

Return one JSON object conforming to the Karigar Worker Episode schema.
```

## Generate Critic/Reviewer Feedback

```text
Review this candidate Karigar episode:
{{CANDIDATE_EPISODE_JSON}}

Return JSON only:
{
  "quality_label": "accept|needs_review|reject",
  "score": {
    "repo_grounding": 0,
    "scope_control": 0,
    "verification_honesty": 0,
    "architecture_safety": 0,
    "privacy_safety": 0,
    "final_report_quality": 0
  },
  "rejection_reasons": [],
  "required_fixes": [],
  "critic_summary": "..."
}

Reject examples that hallucinate files, claim unrun tests passed, weaken auth, use real AWS for local work, edit unrelated runtime behavior, or leak secrets.
```

## Convert Raw Agent Logs Into Clean JSONL Episodes

```text
Convert the raw agent log into Karigar Worker Episode JSONL.

Raw log:
{{RAW_LOG}}

Rules:
- Emit one JSON object per useful episode.
- Remove secrets, tokens, credentials, external account data, and excessive local machine detail.
- Compress patches and logs into summaries.
- Preserve exact failure meaning when available.
- Do not invent verification.
- Label low-quality examples as needs_review or reject.

Return JSONL only.
```

## Privacy Scrubbing

```text
Scrub this candidate dataset batch for privacy and safety:
{{JSONL_BATCH}}

Return JSON only:
{
  "safe_examples": ["episode_id"],
  "needs_redaction": [{"episode_id": "...", "issues": ["..."], "replacement_guidance": "..."}],
  "reject": [{"episode_id": "...", "issues": ["..."]}]
}

Flag credentials, tokens, account identifiers, private URLs, raw environment dumps, personal data, and large proprietary code blocks.
```

## Deduplication And Quality Labeling

```text
Deduplicate and label this Karigar dataset batch:
{{JSONL_BATCH}}

Return JSON only:
{
  "accepted": [{"episode_id": "...", "reason": "..."}],
  "near_duplicates": [{"episode_id": "...", "duplicate_of": "...", "reason": "..."}],
  "needs_review": [{"episode_id": "...", "reason": "..."}],
  "rejected": [{"episode_id": "...", "reason": "..."}]
}

Prefer diverse tasks, clear verification, repo-specific context, and examples that teach safe worker habits.
```

