# DEPRECATED: Python Local Worker

**Status:** Deprecated as of 2026-04-26

The Python-based local worker (`worker.py`) is deprecated in favor of the **Tauri/Rust worker app** at `../../worker-app/`.

## Why?

The Tauri worker provides:
- **OpenCode Server Mode**: Native HTTP API integration with `opencode serve` instead of CLI subprocesses
- **LiteLLM Proxy Management**: Automatic lifecycle management of the local LiteLLM proxy for model routing and rate-limit fallbacks
- **Circuit Breakers**: Multi-layer hard limits (TTL, token caps, identical failure detection, budget caps) to prevent infinite loops
- **SQS Checkpoint Events**: Hybrid delete-on-receipt + periodic status events for real-time dashboard visibility
- **AGENTS.md Sandboxing**: Automatic constraint injection and permission auto-approve/deny
- **Desktop GUI**: Built-in status dashboard, job history, and live logs

## Migration

1. Install the Tauri worker app from `worker-app/`
2. Pair it with the backend via the dashboard
3. Set engine to `opencode-server` in settings
4. The Tauri worker will automatically manage LiteLLM and OpenCode server processes

## Support Timeline

- **Now:** Python worker still functions but prints deprecation warning
- **Future:** Will be removed in a future release. Do not build new features against this implementation.
