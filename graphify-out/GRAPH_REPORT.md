# Graph Report - .  (2026-04-25)

## Corpus Check
- 114 files · ~88,568 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 869 nodes · 1977 edges · 85 communities detected
- Extraction: 58% EXTRACTED · 42% INFERRED · 0% AMBIGUOUS · INFERRED: 837 edges (avg confidence: 0.67)
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

## God Nodes (most connected - your core abstractions)
1. `FileManager` - 108 edges
2. `MockLLMService` - 63 edges
3. `DynamoDBRepository` - 60 edges
4. `get_repository()` - 60 edges
5. `MemoryService` - 58 edges
6. `LLMService` - 55 edges
7. `ScoringService` - 54 edges
8. `InMemoryRepository` - 51 edges
9. `RelationshipService` - 45 edges
10. `Repository` - 44 edges

## Surprising Connections (you probably didn't know these)
- `ProjectMemory` --uses--> `Service for managing project memory entries.`  [INFERRED]
  backend\app\repository.py → backend\app\services\memory.py
- `Idea` --uses--> `ProjectTwinService`  [INFERRED]
  backend\app\repository.py → backend\app\services\project_twin.py
- `Idea` --uses--> `MockLLMService`  [INFERRED]
  backend\app\repository.py → backend\tests\conftest.py
- `Idea` --uses--> `FakeSession`  [INFERRED]
  backend\app\repository.py → backend\tests\conftest.py
- `Idea` --uses--> `Test fixtures for Idea Refinery backend tests.`  [INFERRED]
  backend\app\repository.py → backend\tests\conftest.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (100): list_ai_models(), get_build_prompts(), get_current_step(), get_service(), BuildHandoffService, Generate a comprehensive Prometheus planning prompt for the entire project., Generate a comprehensive Prometheus planning prompt for the entire project., Generate step-by-step build prompts for Prometheus. (+92 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (73): BaseModel, _build_context(), get_chat_history(), send_chat_message(), websocket_chat(), create_idea(), delete_idea(), _get_composite_score() (+65 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (29): ProjectTwinService, to_jsonable(), get_job(), get_project_twin(), get_service(), GitHubImportRequest, import_github_project(), list_idea_jobs() (+21 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (42): db_session(), FakeSession, mock_llm(), MockLLMService, Test fixtures for Idea Refinery backend tests., Mock LLM service that returns canned responses., sample_idea(), sample_idea_two() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (34): IdeaRefineryWorker, main(), WorkerClient, Tests for the Chat API (REST endpoints; WebSocket tested via REST history)., Happy path: GET chat history for idea with no messages returns empty list., Edge case: GET chat history for nonexistent idea returns 404., Happy path: POST chat message returns assistant response., Edge case: POST chat message for nonexistent idea returns 404. (+26 more)

### Community 5 - "Community 5"
Cohesion: 0.1
Nodes (39): create_or_update_memory(), delete_memory(), get_all_global_memory(), get_idea_memory(), get_service(), _memory_to_dict(), MemoryCreate, MemoryResponse (+31 more)

### Community 6 - "Community 6"
Cohesion: 0.1
Nodes (35): compare_ideas(), CompareRequest, get_composite_score(), get_scores(), get_service(), AI scores idea on all 7 dimensions., Get all scores for an idea., Get composite (weighted average) score. (+27 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (1): InMemoryRepository

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (35): _extract_topic(), generate_research_prompts(), GenerateResponse, get_service(), integrate_research(), IntegrateResponse, list_research_tasks(), _parse_prompts() (+27 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (1): Repository

### Community 10 - "Community 10"
Cohesion: 0.14
Nodes (14): Base, Compatibility placeholder; production persistence is DynamoDB-backed., _mock_chat_completion(), _mock_chat_completion_sync(), _mock_llm_init(), Test server entry point with mocked LLM service.  This module patches all LLM ca, Drop and recreate database tables for clean test state., Replace LLMService init to avoid real API connections. (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (6): GitHubAppService, GitHub App helper for installation metadata and short-lived tokens., get_service(), github_app_webhook(), list_installation_repos(), GitHubInstallation

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (9): _RateLimiter, Synchronous DuckDuckGo search call., Return cached results if still valid., Store results in cache., Simple in-memory sliding window rate limiter., Web search service using DuckDuckGo with rate limiting and caching., Search the web and return list of {title, url, snippet}.          Returns empty, Fetch a URL and extract readable text.          Returns empty string on failure (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.26
Nodes (7): api(), apiDelete(), apiPost(), apiPut(), buildUrl(), loadProject(), reindex()

### Community 14 - "Community 14"
Cohesion: 0.2
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.5
Nodes (1): active

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (2): BaseSettings, Settings

### Community 20 - "Community 20"
Cohesion: 0.67
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.67
Nodes (1): MockWebSocket

### Community 22 - "Community 22"
Cohesion: 0.67
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.67
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
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
Nodes (1): Mock LLM service that returns canned responses.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Create an in-memory SQLite database and session for each test.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Create an httpx AsyncClient with ASGITransport for API testing.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Create a MockLLMService with default canned responses.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Create a test idea in the database.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Create a second test idea for relationship testing.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Create a temporary directory for file manager tests.

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Service for managing project memory entries (key-value store with categories).

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Create or update a ProjectMemory record.

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): Return a specific memory entry.

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): Return all memory entries (global if idea_id=None, per-idea otherwise).

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Delete a memory entry. Returns True if deleted, False if not found.

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Return all memory entries for a category.

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Return formatted memory text for inclusion in LLM system prompts.

## Knowledge Gaps
- **49 isolated node(s):** `Compatibility placeholder; production persistence is DynamoDB-backed.`, `Simple in-memory sliding window rate limiter.`, `Web search service using DuckDuckGo with rate limiting and caching.`, `Search the web and return list of {title, url, snippet}.          Returns empty`, `Fetch a URL and extract readable text.          Returns empty string on failure` (+44 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 25`** (2 nodes): `init_db.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `App.svelte`, `main.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `Actions.svelte`, `Actions.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `Reports.svelte`, `Reports.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `playwright.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `start.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `database.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `lambda_handler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `idea-lifecycle.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `idea-relationships.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `research-flow.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `svelte.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Counter.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `api.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `BuildQueue.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `FileUpload.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `ResearchTaskCard.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `ChatInput.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `MarkdownRenderer.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `MessageBubble.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `MessageList.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `PhaseIndicator.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `CreateIdea.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `ImportProject.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `ScoreBar.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `AppShell.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Sidebar.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `ReportViewer.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Badge.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Card.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Input.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Modal.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `app-stores.svelte.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `+page.svelte`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `configure_api_custom_domain.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `create_amplify_app.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `deploy_aws_backend.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `install_idearefinery_worker.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Mock LLM service that returns canned responses.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Create an in-memory SQLite database and session for each test.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Create an httpx AsyncClient with ASGITransport for API testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Create a MockLLMService with default canned responses.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Create a test idea in the database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Create a second test idea for relationship testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Create a temporary directory for file manager tests.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `Service for managing project memory entries (key-value store with categories).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `Create or update a ProjectMemory record.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `Return a specific memory entry.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `Return all memory entries (global if idea_id=None, per-idea otherwise).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `Delete a memory entry. Returns True if deleted, False if not found.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `Return all memory entries for a category.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Return formatted memory text for inclusion in LLM system prompts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_repository()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 11`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Why does `FileManager` connect `Community 0` to `Community 8`, `Community 1`, `Community 3`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Why does `InMemoryRepository` connect `Community 7` to `Community 9`, `Community 3`, `Community 1`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `FileManager` (e.g. with `BuildHandoffService` and `Service for generating Prometheus build handoff prompts and tracking build progr`) actually correct?**
  _`FileManager` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `MockLLMService` (e.g. with `Idea` and `IdeaRelationship`) actually correct?**
  _`MockLLMService` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `get_repository()` (e.g. with `websocket_chat()` and `get_chat_history()`) actually correct?**
  _`get_repository()` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `MemoryService` (e.g. with `MemoryCreate` and `MemoryResponse`) actually correct?**
  _`MemoryService` has 50 INFERRED edges - model-reasoned connections that need verification._