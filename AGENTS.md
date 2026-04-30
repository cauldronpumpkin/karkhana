## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## OpenCode cost-aware model routing

Two providers serve this project:

| Provider | Type | Models | Role |
|---|---|---|---|
| `codex-lb` | Custom (npm) | gpt-5.5, gpt-5.4-mini | Premium planning, code writing |
| `opencode-go` | Built-in | deepseek-v4-flash, deepseek-v4-pro | Exploration, hard debugging |

Agent routing:

| Agent | Model | Cost | Purpose |
|---|---|---|---|
| `build` (default) | gpt-5.4-mini | cheap | Code writing — exclusive |
| `plan` | gpt-5.5 | premium | Architecture, planning, risk |
| `explore-cheap` | deepseek-v4-flash | cheap | Repo exploration (massive context) |
| `coder-cheap` | gpt-5.4-mini | cheap | Implementation subagent |
| `review-cheap` | deepseek-v4-flash | cheap | Code review (large context) |
| `code-goblin` | deepseek-v4-flash | cheap | Adversarial edge-case hunter |
| `architect-premium` | gpt-5.5 | premium | Architecture fallback |
| `staff-engineer` | deepseek-v4-pro | mid | Hard debugging specialist only |

Commands: `/cheap-fix`, `/cheap-review`, `/explore-cheap`, `/deep-plan`, `/premium-review`, `/staff-engineer`, `/goblin`

## Skill-Aware Agent Routing (Option D)

The routing config at `.opencode/agent-skills.json` maps 34 skills to subagents with trigger keyword matching.

### How it works

1. **Task description** is matched against trigger keywords for each skill
2. **Best matching skill** is selected by trigger score
3. **Correct subagent** is chosen based on skill → subagent mapping
4. **Skill is injected** into the subagent prompt: `"Load the {skill} skill using the skill tool"`
5. **Review chain** runs automatically with skill-loaded reviewer

### Smart router command

`/route <task>` — Analyzes the task and auto-selects the best subagent + skill combo.

### Skill-loaded commands (direct access)

| Command | Skill | Subagent | Use for |
|---|---|---|---|
| `/fastapi <task>` | fastapi-expert | coder-cheap | FastAPI endpoints, Pydantic models |
| `/nextjs <task>` | nextjs-developer | coder-cheap | Next.js 14+ App Router features |
| `/python <task>` | python-pro | coder-cheap | Python with type safety, tests |
| `/test <task>` | test-master | coder-cheap | Test strategies, coverage |
| `/security-audit <target>` | security-reviewer | review-cheap + code-goblin | Vulnerability hunting |
| `/debug <error>` | debugging-wizard | explore-cheap | Systematic debugging |
| `/fullstack <task>` | fullstack-guardian | coder-cheap | End-to-end features (DB→API→UI) |
| `/architect <task>` | architecture-designer | architect-premium | System design, ADRs |
| `/sql <task>` | sql-pro | coder-cheap | Query optimization, schema design |
| `/devops <task>` | devops-engineer | coder-cheap | Docker, CI/CD, Terraform, K8s |
| `/spec <feature>` | feature-forge | architect-premium | Requirements, user stories |

### Manual skill loading in subagent prompts

When delegating to any subagent via the Task tool, include skill loading:

```
Task(
  subagent_type: "coder-cheap",
  prompt: "Load the 'fastapi-expert' skill using the skill tool, then implement..."
)
```

### Multi-skill tasks

For tasks spanning domains, load multiple skills in the subagent prompt:

```
Task(
  subagent_type: "coder-cheap",
  prompt: "Load both 'fastapi-expert' AND 'sql-pro' skills, then implement the endpoint with optimized queries..."
)
```

## Parallel Execution

OpenCode supports true concurrent subagent execution by emitting multiple `Task()` calls in a single response block.

### How it works

1. **Orchestrator** (the `build` agent) decomposes a task into subtasks with **disjoint write scopes**
2. **Multiple Task() calls** are emitted in one response — they run concurrently
3. **Each worker** is restricted to its assigned write paths
4. **Reconciliation** is done serially by the orchestrator after all workers finish
5. **Verification** runs as a second parallel wave (reviewers + test runner)

### Parallel commands

| Command | Purpose |
|---|---|
| `/parallel <task>` | Full fan-out/fan-in execution — parallel implementation + review |
| `/parallel-review` | Parallel read-only review only — dispatches review-cheap + code-goblin + test runner |
| `/parallel-plan <task>` | Dry run — produces a fan-out plan without dispatching workers |
| `/parallel-safe <task>` | Diagnostic — classifies whether a task is safe to parallelize |

### Safety rules

- Workers must have **disjoint write paths** — no two workers editing the same files
- **God nodes** (Repository, FactoryRunService, FileManager, etc.) are serialization boundaries — never parallelize edits to them
- **Shared files** (package.json, config files, shared API clients) are **orchestrator-only** — workers document needed changes instead of editing
- Each worker returns a **structured handoff** with status, files changed, and proposed shared-file changes

### When to use parallel vs serial

**Use `/parallel` for:**
- Frontend + backend features with a clear API contract
- Independent components in different file trees
- Implementation + docs + tests for distinct modules
- Any task with natural file-scope boundaries

**Use serial (`/route`) for:**
- Edits to core abstractions (god nodes)
- Database migrations
- Package manifest or config changes
- Broad refactors or renames
- Auth/security middleware

### Example

```
/parallel Add project tags: backend CRUD API and frontend tag editor
```

This dispatches:
- Wave 1: `coder-cheap+fastapi-expert` (backend) + `coder-cheap+frontend-design` (frontend) — **in parallel**
- Reconciliation: orchestrator wires up shared files serially
- Wave 2: `review-cheap` + `code-goblin` + `coder-cheap` (tests) — **in parallel**
