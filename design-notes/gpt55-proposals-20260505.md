# Karkhana Design Proposals (GPT-5.5, 2026-05-05)

> Generated via codex-lb/gpt-5.5 during credit-burn session. Pick up after 4-week plan (Week 3-4+).

## 1. Hybrid Memory Strategy (Honcho + FTS5)

Three-layer memory: existing MemoryService (episodic) + FTS5 SQLite index (lexical recall) + Honcho (dialectic user modeling).

FTS5 remembers *what was said* — exact file paths, error messages, decisions. Honcho models *who you are* — preferences, style, recurring goals.

Full proposal with schemas, code, and integration points in the original API output.

## 2. WebSocket Streaming Protocol

Real-time job status streaming for worker dashboards. Message types, reconnection strategy, auth. JSON schemas defined.

## 3. Autonomy Level 2 Auto-Repair

State machine for detect → classify → retry → escalate on failed factory runs. Circuit breaker integration. Guardrail design.

## 4. Plugin Engine System

Third-party AI engine registration with capability discovery and sandboxing. OpenCodeEngine / HermesAgentEngine / CodexEngine pattern extended.

## 5. RBAC Model (GitHub OAuth)

Project owners, org admins, worker agents, auditors. Full permission matrix.

## 6. Multi-Region DynamoDB Strategy

Global tables for 10K+ daily factory runs. Capacity planning, cost estimates.

## 7. "Karkhana Builds Karkhana" Architecture

Workers claim Karkhana dev tasks from Karkhana backend, execute, auto-submit PRs.

## 8. Cost Attribution System

LLM token tracking per project/phase/worker. Weekly cost reports. Model comparison dashboard.

## 9. OpenTelemetry Observability

Traces across API → SQS → Worker → Result. Prometheus + Grafana dashboards.

## 10. Notification System

Email (SendGrid), Slack webhooks, Telegram bot, in-app toasts. Delivery guarantees and retry.

## 11. CI/CD Improvements

Faster feedback loops for GitHub Actions. Parallelization suggestions.

## 12. Factory Orchestrator Scaling

Scaling factory_orchestrator.py to 100+ concurrent runs. Lambda-friendly patterns.
