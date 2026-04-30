# Parallel Orchestration Protocol

Parallel workers share one filesystem. They must obey assigned write paths.

## Rules

1. **Only edit files listed in `write_paths`** — no exceptions.
2. **Do not edit shared config** unless explicitly assigned by the orchestrator.
3. **Do not modify god nodes** during a parallel wave.
4. **Return a structured handoff** when finished.
5. **The orchestrator owns reconciliation** — never commit or run broad formatters.

## Serialization Boundaries (God Nodes)

These files/abstractions must NEVER be edited by parallel workers:

| God Node | Location(s) |
|----------|-------------|
| `InMemoryRepository` | `backend/app/repository.py` |
| `DynamoDBRepository` | `backend/app/repository.py` |
| `Repository` | `backend/app/repository.py` |
| `get_repository()` | `backend/app/repository.py` |
| `FactoryRunService` | `backend/app/services/factory_run.py` |
| `FileManager` | `backend/app/services/file_manager.py` |
| `ProjectTwinService` | `backend/app/services/project_twin.py` |
| `FactoryRun` | `backend/app/models/` |

## Shared Files (Orchestrator-Only)

These files are owned by the orchestrator and must not be edited by parallel workers:

- `package.json`, `package-lock.json`, `pyproject.toml`, `requirements*.txt`
- `opencode.json`, `.opencode/agent-skills.json`
- `vite.config.*`, `svelte.config.*`, `tsconfig.json`, `pytest.ini`
- `backend/app/main.py`, `backend/app/repository.py`
- `frontend/src/lib/api.js` (or equivalent shared API client)

## Safe Parallelization Targets

- Independent frontend components
- Frontend + backend with stable API contract
- Independent route/module additions
- Docs + tests
- Multiple read-only reviewers
- Multiple read-only investigations

## Never Parallelize

- Shared persistence abstractions (Repository, models)
- Auth/security middleware
- Database migrations + app model changes in one wave
- Package manifest changes
- Broad renames/moves
- Cross-cutting formatting
