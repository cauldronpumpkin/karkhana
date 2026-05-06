# Factory Orchestrator Scaling (100+ Concurrent Runs)

**Source:** GPT-5.5 via codex-lb, 2026-05-05 | **6,282 tokens**

## 1. SQS + Lambda Fanout (not in-process)

Move orchestration out of process memory. `start_run()` writes to DynamoDB + SQS, returns immediately. SQS-triggered Lambda workers execute each task. Reserved concurrency at 150. No more `asyncio.gather` bottleneck.

## 2. DynamoDB Single-Table Design

Key layout:
```
RUN#abc    META            (run metadata, immutable-ish)
RUN#abc    TASK#task-001    (one item per task)
RUN#abc    COUNTER#0-15     (sharded counters, 16 shards)
```

- GSI for run status queries (no scans)
- S3 for large results (store pointers, not blobs)
- BatchWriteItem for task creation
- Conditional writes only for claims and terminal transitions

## 3. Retry-Safe Task State Machine

```
QUEUED → RUNNING → SUCCEEDED / FAILED / TIMED_OUT
```

- Lease on RUNNING (5 min expiry)
- Conditional claim: only if QUEUED OR lease expired
- Heartbeat for long-running tasks
- Terminal update conditional on worker_id match
- Counter increment only AFTER successful terminal transition
- Reaper Lambda (EventBridge, every 1 min) requeues expired leases
- GSI on expired leases for efficient reaping

## Full Code

See original GPT-5.5 output for: SQS batch dispatch, Lambda worker handler, claim/renew/reap functions, sharded counter implementation, GSI patterns.
