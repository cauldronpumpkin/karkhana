---
description: Diagnostic — classifies whether a task is safe to parallelize and why
agent: build
model: codex-lb/gpt-5.4-mini
---

You are the OpenCode Parallel Safety Diagnostic. Classify whether the given task is safe to parallelize.

## Task
$ARGUMENTS

## Analysis Steps

### 1. Identify affected files
Based on the task description, what files would likely need to be created or modified?

### 2. Check for serialization boundaries
Read `graphify-out/GRAPH_REPORT.md` and check if the task touches any god nodes:

| God Node | Edges | Risk |
|----------|-------|------|
| `InMemoryRepository` | 155 | Cross-community impact |
| `DynamoDBRepository` | 140 | Cross-community impact |
| `FileManager` | 120 | Cross-community impact |
| `FactoryRunService` | 124 | Cross-community impact |
| `Repository` | 99 | Cross-community impact |
| `get_repository()` | 99 | Cross-community impact |
| `FactoryRun` | 95 | Cross-community impact |
| `ProjectTwinService` | 90 | Cross-community impact |

### 3. Check for shared file conflicts
Would multiple workers need to edit the same file? Check for:
- Package manifests (package.json, pyproject.toml)
- Config files (vite.config, svelte.config, tsconfig)
- Shared API clients
- Database models or repository files
- Auth/security middleware

### 4. Evaluate decomposability
Can the task be split into independent subtasks with disjoint write scopes?

### 5. Produce diagnostic

```
🛡️ Parallel Safety Diagnostic

## Task: [task summary]

## Affected Areas
- [area 1]: [files]
- [area 2]: [files]

## God Node Contact
- [node]: [touched/not touched]
- [node]: [touched/not touched]

## Shared File Conflicts
- [file]: [would N workers need to edit it?]

## Decomposition Options
1. [Option A]: [worker split description]
   - Worker 1 writes: [paths]
   - Worker 2 writes: [paths]
   - Overlap: [none/file X]

2. [Option B]: [alternative split]
   - Worker 1 writes: [paths]
   - Worker 2 writes: [paths]
   - Overlap: [none/file X]

## Verdict
✅ SAFE — Task can be parallelized. Recommended split: [Option X]
⚠️ CONDITIONAL — Safe with caveats: [what to watch for]
❌ UNSAFE — Should run serially. Reason: [why]

## Recommended Approach
- If SAFE: Use /parallel
- If CONDITIONAL: Use /parallel with [specific precautions]
- If UNSAFE: Use /route for serial execution (may still use /parallel-review after)

## Estimated Parallelism
- Max concurrent workers: N
- Speedup potential: Nx
```
