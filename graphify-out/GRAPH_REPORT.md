# Graph Report - .  (2026-05-07)

## Corpus Check
- 271 files · ~249,126 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2872 nodes · 8718 edges · 107 communities detected
- Extraction: 50% EXTRACTED · 50% INFERRED · 0% AMBIGUOUS · INFERRED: 4383 edges (avg confidence: 0.7)
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
1. `InMemoryRepository` - 159 edges
2. `DynamoDBRepository` - 144 edges
3. `utcnow()` - 109 edges
4. `FactoryRunService` - 108 edges
5. `get_repository()` - 104 edges
6. `Repository` - 100 edges
7. `ProjectTwinService` - 93 edges
8. `ProjectTwin` - 86 edges
9. `FileManager` - 85 edges
10. `FactoryRun` - 81 edges

## Surprising Connections (you probably didn't know these)
- `GitHubInstallation` --uses--> `GitHub App helper for installation metadata and short-lived tokens.`  [INFERRED]
  backend\app\repository.py → backend\app\services\github_app.py
- `WorkItem` --calls--> `test_ledger_path_rejects_traversal_and_absolute_paths()`  [INFERRED]
  backend\app\repository.py → backend\tests\test_worker_capability_assignment.py
- `AI scores idea on all 7 dimensions.` --uses--> `ScoringService`  [INFERRED]
  backend\app\routers\scoring.py → backend\app\services\scoring.py
- `Get all scores for an idea.` --uses--> `ScoringService`  [INFERRED]
  backend\app\routers\scoring.py → backend\app\services\scoring.py
- `Get composite (weighted average) score.` --uses--> `ScoringService`  [INFERRED]
  backend\app\routers\scoring.py → backend\app\services\scoring.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (202): validate_engine_for_autonomy_level(), BaseModel, _build_context(), ChatMessageRequest, get_chat_history(), send_chat_message(), websocket_chat(), db_session() (+194 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (176): can_auto_advance_phase(), can_auto_repair(), can_bypass_repair_limits(), can_enqueue_work(), check_guardrails(), get_autonomy_level(), GuardrailViolation, validate_autonomy_level() (+168 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (56): build_tracking_manifest(), build_tracking_summary(), _coerce_bool(), _coerce_float(), _coerce_int(), compose_worker_prompt(), _iso(), normalize_token_economy() (+48 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (137): EngineMode, resolve_engine_mode(), run_agent(), run_cli_agent(), run_command(), run_server_agent(), CircuitBreaker, count_consecutive_identical() (+129 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (132): Base, Compatibility placeholder; production persistence is DynamoDB-backed., LocalConfig, commandVersion(), Options, Result, Run(), ensureStateDirs() (+124 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (107): AgentsMdArtifactService, AGENTS.md as a versioned Template Artifact.  AGENTS.md is extracted from the pro, Return a lightweight reference dict for inclusion in worker contracts., Manage AGENTS.md as a versioned Template Artifact.      Responsibilities:     -, Read AGENTS.md from disk and store it as a TemplateArtifact., Return a copy with the canonical artifact key., Get the AGENTS.md artifact for a template.          If version is None, returns, List all stored AGENTS.md versions for a template pack. (+99 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (123): ABC, normalize_output_dir(), Write a text artifact., Write a normalized JSON artifact., write_json_artifact(), write_text_artifact(), Minimal command allow-list for the mock runner., Return whether the command is permitted. (+115 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (128): get_build_prompts(), get_current_step(), get_next_actions(), get_service(), _build_context_files(), BuildHandoffService, _codex_prompt(), _opencode_command() (+120 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (113): api_client_builds_consistent_worker_auth_headers(), ApiClient, ApiError, handler(), Tests for the Chat API (REST endpoints; WebSocket tested via REST history)., Happy path: GET chat history for idea with no messages returns empty list., Edge case: GET chat history for nonexistent idea returns 404., Happy path: POST chat message returns assistant response. (+105 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (85): BackendClient, _build_ledger_body(), Send a heartbeat to keep the job claim alive., HTTP client for the Karkhana worker API., Register this worker with the backend. Returns registration details including wo, Post a worker event to the backend., Report job result (convenience alias for complete_job)., Get the current status of a job from the backend. (+77 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (46): Exception, ArtifactPatchProposal, _build_decision_summary(), _build_default_role_manifests(), _compute_confidence(), CouncilSummary, derive_council_summary(), _derive_expert_decision() (+38 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (1): Repository

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (66): api(), apiDelete(), apiPost(), apiPut(), appendQuery(), buildApiUrl(), createFactoryRun(), createResearchArtifact() (+58 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (65): _append_bullet(), _append_table_row(), DynamoDBLedgerService, _escape_table_cell(), extract_compact_ledger_context(), _extract_section(), FactoryRunLedgerError, FactoryRunLedgerService (+57 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (26): list_ai_models(), build(), definition(), FactoryRole, _is_missing(), _render_value(), _resolve_provider(), RoleDefinition (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (37): blueprint_permission_profile_to_worker_policy(), _build_feedback(), _copy_list(), detail(), from_dict(), _from_iso(), _is_broad_scope(), _iso() (+29 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (27): BreakerStatus, BreakerTrigger, canary_warning(), CanaryStateGuard, chrono_now(), CircuitBreakerLimits, civil_from_days(), enter_canary_mode() (+19 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (26): BranchWorkResult, ClaimRequest, ClaimResponse, DraftPullRequestMetadata, FileEntry, Job, JobClaim, JobCompleteRequest (+18 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (11): GitHubAppService, GitHub App helper for installation metadata and short-lived tokens., get_service(), github_app_webhook(), list_installation_repos(), _configure_github_app(), _FakeAsyncClient, test_create_draft_pull_request_requires_active_installation() (+3 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (23): CopyTo(), create_shortcut(), fixup_dbi(), get_root_hkey(), get_shortcuts_folder(), get_special_folder_path(), get_system_dir(), install() (+15 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (17): test_build_issue_summary(), test_build_repair_prompt(), test_classify_failure_ambiguous(), test_classify_failure_build(), test_classify_failure_dependency(), test_classify_failure_flaky(), test_classify_failure_integration(), test_classify_failure_lint() (+9 more)

### Community 21 - "Community 21"
Cohesion: 0.15
Nodes (11): CreateSessionRequest, FileDiff, HealthResponse, MessagePart, MessageResponse, ModelRef, OpenCodeError, PermissionResponse (+3 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.2
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.62
Nodes (6): binaryName(), candidateBinaries(), main(), printMissingBinaryHelp(), repoRoot(), run()

### Community 25 - "Community 25"
Cohesion: 0.4
Nodes (2): MockFormData, MockWebSocket

### Community 26 - "Community 26"
Cohesion: 0.4
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.4
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 0.5
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 0.5
Nodes (1): active

### Community 31 - "Community 31"
Cohesion: 0.5
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 0.67
Nodes (2): BaseSettings, Settings

### Community 33 - "Community 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 0.67
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 0.67
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 0.67
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 0.67
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 0.67
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 0.67
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
Nodes (1): active

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): active

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
Nodes (0): 

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (0): 

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (0): 

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (0): 

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (0): 

### Community 98 - "Community 98"
Cohesion: 1.0
Nodes (0): 

### Community 99 - "Community 99"
Cohesion: 1.0
Nodes (0): 

### Community 100 - "Community 100"
Cohesion: 1.0
Nodes (0): 

### Community 101 - "Community 101"
Cohesion: 1.0
Nodes (0): 

### Community 102 - "Community 102"
Cohesion: 1.0
Nodes (0): 

### Community 103 - "Community 103"
Cohesion: 1.0
Nodes (0): 

### Community 104 - "Community 104"
Cohesion: 1.0
Nodes (0): 

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (0): 

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **119 isolated node(s):** `WebSocket connection manager with optional Redis pub/sub for multi-instance scal`, `Lazy-load Redis client. Returns None if Redis is unavailable.`, `Manages active WebSocket connections with optional per-user targeting.`, `Accept the WebSocket and register it.`, `Remove a WebSocket from the registry.` (+114 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 40`** (2 nodes): `init_db.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (2 nodes): `mockResponse()`, `api.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (2 nodes): `Actions.svelte`, `Actions.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (2 nodes): `FileUpload.svelte`, `FileUpload.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (2 nodes): `LedgerDetail.svelte`, `return()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (2 nodes): `Reports.svelte`, `Reports.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (2 nodes): `decisionTone()`, `ExpertCouncilCard.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (2 nodes): `summaryDecisionTone()`, `ExpertCouncilPanel.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (2 nodes): `ReviewCockpitDetail.svelte`, `impactTone()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (2 nodes): `ReviewCockpitList.svelte`, `active`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (2 nodes): `Invoke-AwsText()`, `create_amplify_app.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (2 nodes): `App.svelte`, `main.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (2 nodes): `active`, `LiveLogs.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `playwright.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `push-fixes.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `start.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `database.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `idea-lifecycle.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `idea-relationships.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `research-flow.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `svelte.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Counter.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `api.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `BuildQueue.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `ResearchTaskCard.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `ChatInput.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `MarkdownRenderer.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `MessageBubble.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `MessageList.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `PhaseIndicator.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `CreateIdea.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `ImportProject.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `ScoreBar.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `PromptInspector.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `AppShell.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `Sidebar.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `LedgerList.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `LedgerTimeline.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `ReportViewer.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Badge.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Card.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `Input.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `Modal.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `app-stores.svelte.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (1 nodes): `activate_this.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (1 nodes): `configure_api_custom_domain.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 95`** (1 nodes): `deploy_aws_backend.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 96`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 97`** (1 nodes): `ErrorBoundary.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 98`** (1 nodes): `ConfigEditor.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 99`** (1 nodes): `PairingFlow.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 100`** (1 nodes): `StatusPanel.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 101`** (1 nodes): `Badge.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 102`** (1 nodes): `Button.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 103`** (1 nodes): `Card.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 104`** (1 nodes): `Input.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Modal.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `conftest.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Repository` connect `Community 11` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `InMemoryRepository` connect `Community 2` to `Community 0`, `Community 1`, `Community 5`, `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `DynamoDBRepository` connect `Community 2` to `Community 0`, `Community 1`, `Community 5`, `Community 8`, `Community 9`, `Community 11`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 57 inferred relationships involving `InMemoryRepository` (e.g. with `MockLLMService` and `FakeSession`) actually correct?**
  _`InMemoryRepository` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `DynamoDBRepository` (e.g. with `TestWorkItemLedgerFields` and `TestClaimJobAssignmentValidation`) actually correct?**
  _`DynamoDBRepository` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 132 inferred relationships involving `str` (e.g. with `api_req()` and `oc_req()`) actually correct?**
  _`str` has 132 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `utcnow()` (e.g. with `generate_deterministic_review()` and `.create_factory_run()`) actually correct?**
  _`utcnow()` has 48 INFERRED edges - model-reasoned connections that need verification._