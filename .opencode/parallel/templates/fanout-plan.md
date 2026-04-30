# Fan-Out Plan Template

## Task
{{user_task}}

## Parallel Safety
- Safe: [yes/no]
- Reason: [why parallelization is or isn't safe]
- Shared files: [files needed by multiple workers]
- Serialization boundaries: [god nodes or shared abstractions touched]

## API/Data Contract (if frontend + backend)
```json
{
  "endpoint": "",
  "method": "",
  "request": {},
  "response": {}
}
```

## Waves

### Wave 1: Implementation

| ID | Agent | Skill | Objective | Write Paths | Forbidden Paths | Validation |
|---|---|---|---|---|---|---|

### Wave 2: Verification (always parallel, always read-only)

| ID | Agent | Objective | Mode |
|---|---|---|---|
| quality-review | review-cheap | Broad code review | read-only |
| adversarial-review | code-goblin | Edge cases and integration risks | read-only |
| test-runner | coder-cheap | Run focused tests | read-only unless fixing test-only files |

## Merge Plan
- Shared file changes needed by workers:
- Contract alignment checks:
- Integration test commands:
