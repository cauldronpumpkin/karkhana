# Graph Report - .  (2026-04-28)

## Corpus Check
- 191 files · ~149,033 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1818 nodes · 5049 edges · 107 communities detected
- Extraction: 50% EXTRACTED · 50% INFERRED · 0% AMBIGUOUS · INFERRED: 2518 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]

## God Nodes (most connected - your core abstractions)
1. `InMemoryRepository` - 126 edges
2. `DynamoDBRepository` - 120 edges
3. `FileManager` - 108 edges
4. `Repository` - 89 edges
5. `get_repository()` - 88 edges
6. `FactoryRunService` - 85 edges
7. `utcnow()` - 81 edges
8. `FactoryRun` - 71 edges
9. `ProjectTwinService` - 68 edges
10. `MockLLMService` - 63 edges

## Surprising Connections (you probably didn't know these)
- `GitHubInstallation` --uses--> `GitHub App helper for installation metadata and short-lived tokens.`  [INFERRED]
  backend\app\repository.py → backend\app\services\github_app.py
- `AI scores idea on all 7 dimensions.` --uses--> `ScoringService`  [INFERRED]
  backend\app\routers\scoring.py → backend\app\services\scoring.py
- `Get all scores for an idea.` --uses--> `ScoringService`  [INFERRED]
  backend\app\routers\scoring.py → backend\app\services\scoring.py
- `Get composite (weighted average) score.` --uses--> `ScoringService`  [INFERRED]
  backend\app\routers\scoring.py → backend\app\services\scoring.py
- `Manual override for a single dimension score.` --uses--> `ScoringService`  [INFERRED]
  backend\app\routers\scoring.py → backend\app\services\scoring.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (158): list_ai_models(), get_build_prompts(), get_current_step(), get_service(), BuildHandoffService, Generate a comprehensive Prometheus planning prompt for the entire project., Generate a comprehensive Prometheus planning prompt for the entire project., Generate step-by-step build prompts for Prometheus. (+150 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (108): can_auto_advance_phase(), can_auto_repair(), can_bypass_repair_limits(), can_enqueue_work(), check_guardrails(), get_autonomy_level(), GuardrailViolation, validate_autonomy_level() (+100 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (46): build_tracking_manifest(), build_tracking_summary(), compose_worker_prompt(), _iso(), _status_counter(), _work_item_from_batch(), _work_item_status(), handler() (+38 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (98): EngineMode, is_limited_engine(), is_valid_for_high_autonomy(), resolve_engine_mode(), run_agent(), run_cli_agent(), run_command(), run_server_agent() (+90 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (99): BaseModel, create_factory_run(), CreateFactoryRunRequest, get_factory_run(), get_service(), list_factory_runs(), approve_request(), deny_request() (+91 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (63): process_logo(), SqsMessage, SqsTransport, Tests for the Chat API (REST endpoints; WebSocket tested via REST history)., Happy path: GET chat history for idea with no messages returns empty list., Edge case: GET chat history for nonexistent idea returns 404., Happy path: POST chat message returns assistant response., Edge case: POST chat message for nonexistent idea returns 404. (+55 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (14): InMemoryRepository, set_repository(), repo(), repo(), repo(), _blocked_blueprint(), test_factory_run_service_blocked_blueprint_creates_no_run(), test_factory_run_service_valid_blueprint_includes_policy_payload() (+6 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (63): _build_context(), ChatMessageRequest, get_chat_history(), send_chat_message(), websocket_chat(), db_session(), FakeSession, mock_llm() (+55 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (1): Repository

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (51): ABC, blueprint_permission_profile_to_worker_policy(), _build_feedback(), _copy_list(), detail(), from_dict(), _from_iso(), _is_broad_scope() (+43 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (40): create_or_update_memory(), delete_memory(), get_all_global_memory(), get_idea_memory(), get_service(), _memory_to_dict(), MemoryCreate, MemoryResponse (+32 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (27): Exception, test_build_issue_summary(), test_build_repair_prompt(), test_classify_failure_ambiguous(), test_classify_failure_build(), test_classify_failure_dependency(), test_classify_failure_flaky(), test_classify_failure_integration() (+19 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (29): build(), definition(), FactoryRole, _is_missing(), _render_value(), _resolve_provider(), RoleDefinition, RolePromptBuilder (+21 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (20): AgentsMdArtifactService, AGENTS.md as a versioned Template Artifact.  AGENTS.md is extracted from the pro, Return a lightweight reference dict for inclusion in worker contracts., Manage AGENTS.md as a versioned Template Artifact.      Responsibilities:     -, Read AGENTS.md from disk and store it as a TemplateArtifact., Return a copy with the canonical artifact key., Get the AGENTS.md artifact for a template.          If version is None, returns, List all stored AGENTS.md versions for a template pack. (+12 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (23): BranchWorkResult, ClaimRequest, ClaimResponse, FileEntry, Job, JobClaim, JobCompleteRequest, JobFailRequest (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (23): CopyTo(), create_shortcut(), fixup_dbi(), get_root_hkey(), get_shortcuts_folder(), get_special_folder_path(), get_system_dir(), install() (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (14): api(), apiDelete(), apiPost(), apiPut(), buildUrl(), createFactoryRun(), getFactoryRun(), getFactoryRunJobs() (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (14): Base, Compatibility placeholder; production persistence is DynamoDB-backed., _mock_chat_completion(), _mock_chat_completion_sync(), _mock_llm_init(), Test server entry point with mocked LLM service.  This module patches all LLM ca, Drop and recreate database tables for clean test state., Replace LLMService init to avoid real API connections. (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.24
Nodes (5): GitHubAppService, GitHub App helper for installation metadata and short-lived tokens., get_service(), github_app_webhook(), list_installation_repos()

### Community 19 - "Community 19"
Cohesion: 0.23
Nodes (5): act(), approve(), deny(), revoke(), rotate()

### Community 20 - "Community 20"
Cohesion: 0.2
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.22
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.4
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.4
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.4
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 0.5
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (1): active

### Community 27 - "Community 27"
Cohesion: 0.67
Nodes (2): BaseSettings, Settings

### Community 28 - "Community 28"
Cohesion: 0.67
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 0.67
Nodes (1): MockWebSocket

### Community 30 - "Community 30"
Cohesion: 0.67
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 0.67
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 0.67
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (0): 

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (0): 

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (0): 

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (0): 

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (0): 

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (0): 

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (0): 

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (0): 

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (0): 

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (0): 

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (0): 

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (0): 

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (0): 

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (0): 

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (0): 

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (0): 

### Community 93 - "Community 93"
Cohesion: 1.0
Nodes (1): Mock LLM service that returns canned responses.

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (1): Create an in-memory SQLite database and session for each test.

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (1): Create an httpx AsyncClient with ASGITransport for API testing.

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (1): Create a MockLLMService with default canned responses.

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (1): Create a test idea in the database.

### Community 98 - "Community 98"
Cohesion: 1.0
Nodes (1): Create a second test idea for relationship testing.

### Community 99 - "Community 99"
Cohesion: 1.0
Nodes (1): Create a temporary directory for file manager tests.

### Community 100 - "Community 100"
Cohesion: 1.0
Nodes (1): Service for managing project memory entries (key-value store with categories).

### Community 101 - "Community 101"
Cohesion: 1.0
Nodes (1): Create or update a ProjectMemory record.

### Community 102 - "Community 102"
Cohesion: 1.0
Nodes (1): Return a specific memory entry.

### Community 103 - "Community 103"
Cohesion: 1.0
Nodes (1): Return all memory entries (global if idea_id=None, per-idea otherwise).

### Community 104 - "Community 104"
Cohesion: 1.0
Nodes (1): Delete a memory entry. Returns True if deleted, False if not found.

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Return all memory entries for a category.

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (1): Return formatted memory text for inclusion in LLM system prompts.

## Knowledge Gaps
- **93 isolated node(s):** `Compatibility placeholder; production persistence is DynamoDB-backed.`, `Simple in-memory sliding window rate limiter.`, `Web search service using DuckDuckGo with rate limiting and caching.`, `Search the web and return list of {title, url, snippet}.          Returns empty`, `Fetch a URL and extract readable text.          Returns empty string on failure` (+88 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 34`** (2 nodes): `init_db.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (2 nodes): `App.svelte`, `main.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (2 nodes): `Actions.svelte`, `Actions.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (2 nodes): `Reports.svelte`, `Reports.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (2 nodes): `Invoke-AwsText()`, `create_amplify_app.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (2 nodes): `App.svelte`, `main.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `playwright.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `start.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `database.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `idea-lifecycle.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `idea-relationships.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `research-flow.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `svelte.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Counter.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `api.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `BuildQueue.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `FileUpload.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `ResearchTaskCard.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `ChatInput.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `MarkdownRenderer.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `MessageBubble.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `MessageList.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `PhaseIndicator.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `CreateIdea.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `ImportProject.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `ScoreBar.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `PromptInspector.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `AppShell.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Sidebar.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `ReportViewer.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Badge.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Card.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Input.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Modal.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `app-stores.svelte.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `activate_this.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `configure_api_custom_domain.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `deploy_aws_backend.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `stores.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `ConfigEditor.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `LiveLogs.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `PairingFlow.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `StatusPanel.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `Badge.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Button.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Card.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Input.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `Modal.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `conftest.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (1 nodes): `Mock LLM service that returns canned responses.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (1 nodes): `Create an in-memory SQLite database and session for each test.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 95`** (1 nodes): `Create an httpx AsyncClient with ASGITransport for API testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 96`** (1 nodes): `Create a MockLLMService with default canned responses.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 97`** (1 nodes): `Create a test idea in the database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 98`** (1 nodes): `Create a second test idea for relationship testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 99`** (1 nodes): `Create a temporary directory for file manager tests.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 100`** (1 nodes): `Service for managing project memory entries (key-value store with categories).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 101`** (1 nodes): `Create or update a ProjectMemory record.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 102`** (1 nodes): `Return a specific memory entry.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 103`** (1 nodes): `Return all memory entries (global if idea_id=None, per-idea otherwise).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 104`** (1 nodes): `Delete a memory entry. Returns True if deleted, False if not found.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Return all memory entries for a category.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `Return formatted memory text for inclusion in LLM system prompts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InMemoryRepository` connect `Community 6` to `Community 1`, `Community 2`, `Community 4`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `get_repository()` connect `Community 2` to `Community 0`, `Community 1`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 13`, `Community 18`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `Repository` connect `Community 8` to `Community 2`, `Community 6`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `InMemoryRepository` (e.g. with `MockLLMService` and `FakeSession`) actually correct?**
  _`InMemoryRepository` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 90 inferred relationships involving `FileManager` (e.g. with `BuildHandoffService` and `Service for generating Prometheus build handoff prompts and tracking build progr`) actually correct?**
  _`FileManager` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 85 inferred relationships involving `get_repository()` (e.g. with `websocket_chat()` and `get_chat_history()`) actually correct?**
  _`get_repository()` has 85 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Compatibility placeholder; production persistence is DynamoDB-backed.`, `Simple in-memory sliding window rate limiter.`, `Web search service using DuckDuckGo with rate limiting and caching.` to the rest of the system?**
  _93 weakly-connected nodes found - possible documentation gaps or missing edges._