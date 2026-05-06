# Hybrid Memory Strategy (Honcho + FTS5)

**Source:** GPT-5.5 via codex-lb, 2026-05-05 | **10,580 tokens output**

## Summary

Three complementary layers replacing/supplementing existing `MemoryService`:

| Layer | Tool | Answers | Data |
|:---|:---|:---|:---|
| Episodic | Existing MemoryService | Current session, summaries | Current impl |
| Lexical | FTS5 SQLite | "Where did we discuss X?" "What was that error?" | `memory_events` + `memory_events_fts` |
| Dialectic | Honcho | "User prefers code over theory." "User is building Karkhana." | Honcho user model |

## Architecture

### Write path
```
user/assistant message → MemoryService.add_message()
  ├─ existing storage/summarization
  ├─ FTS5 index (raw message + tags)
  └─ Honcho observe (sanitized)
```

### Read path
```
incoming query → MemoryService.build_memory_context()
  ├─ recent messages
  ├─ existing semantic memories
  ├─ FTS5 cross-session hits (BM25 scored)
  └─ Honcho user model/context
      ↓
  rank, dedupe, compress → prompt context
```

## FTS5 Schema

- `memory_sessions`: session metadata (user_id, project_id, timestamps)
- `memory_events`: canonical events (role, kind, content, tags)
- `memory_events_fts`: FTS5 virtual table with SQLite triggers for auto-sync

Event kinds: `message`, `summary`, `decision`, `preference`, `artifact`, `error`, `todo`

Search uses BM25 scoring with `snippet()` for context.

## Honcho Adapter

`HonchoUserModel` wraps all Honcho SDK calls behind stable interface:
- `observe_message` / `observe_summary` / `observe_decision`
- `get_context` returns `HonchoUserContext` (profile, preferences, goals, style, threads)

FTS5 answers "what happened." Honcho answers "who is this user becoming."

## Ranking Policy
```
final_score = 0.45*semantic + 0.30*bm25 + 0.15*recency + 0.10*kind_boost
```
Kind boost: preference +0.20, decision +0.18, summary +0.15, artifact +0.10

## Implementation Phases

1. **FTS5 only:** index messages, backfill sessions, immediate cross-session recall
2. **Distilled events:** summaries, decisions, preferences as explicit kinds
3. **Honcho:** user modeling, compact context injection
4. **Evaluation:** test prompts for exact recall vs user preference queries

## Full Code

See original GPT-5.5 output (2026-05-05 session) for:
- Complete `FTSMemoryIndex` class with CREATE TABLE/TRIGGER SQL
- `HonchoUserModel` adapter class
- `MemoryService` integration points
- `build_memory_context` merge/dedupe logic
- Configuration/feature flags
- Backfill script
- Privacy filters (API keys, secrets)
