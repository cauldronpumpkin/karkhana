# Command Center API

## Week 1: Agent Communications Foundation

The following APIs are available for read-only inspection and manual resolution of persisted inter-agent messages.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/command-center/jobs/{job_id}/agent-messages` | List all agent messages for a job, oldest-first. |
| `GET` | `/api/command-center/jobs/{job_id}/agent-messages/pending` | List only `pending` agent messages for a job. |
| `POST` | `/api/command-center/jobs/{job_id}/agent-messages/{message_id}/resolve` | Manually resolve an agent message and emit `agent_message_resolved`. |

### Path/Status Contract

- If `job_id` does not exist, all three endpoints return `404` with:

```json
{"error":"Job not found"}
```

- If `message_id` does not exist for the target job on resolve:

```json
{"error":"Agent message not found"}
```

## Data Contracts

### AgentMessage

```json
{
  "id": 12,
  "job_id": "a1b2c3d4e5f6",
  "from_agent": "coder_agent",
  "to_agent": "pm_agent",
  "message_type": "clarification_request",
  "topic": "auth_scope",
  "content_json": {
    "question": "Do we need OAuth in MVP?"
  },
  "status": "pending",
  "blocking": true,
  "created_at": 1740787200.123,
  "resolved_at": null
}
```

### Resolve Request

```json
{
  "decision": {
    "status": "approved",
    "rationale": "Keep MVP focused; defer OAuth.",
    "metadata": {
      "source": "manual"
    }
  }
}
```

### Resolve Response

```json
{
  "ok": true,
  "message": {
    "id": 12,
    "job_id": "a1b2c3d4e5f6",
    "from_agent": "coder_agent",
    "to_agent": "pm_agent",
    "message_type": "clarification_request",
    "topic": "auth_scope",
    "content_json": {
      "question": "Do we need OAuth in MVP?",
      "decision": {
        "status": "approved",
        "rationale": "Keep MVP focused; defer OAuth.",
        "metadata": {
          "source": "manual"
        }
      }
    },
    "status": "resolved",
    "blocking": true,
    "created_at": 1740787200.123,
    "resolved_at": 1740787221.987
  }
}
```

## WebSocket Event Contracts (Week 2 Runtime Schema)

Event types:

- `agent_message_created`
- `agent_message_resolved`
- `agent_message_escalated`

Payload shape:

```json
{
  "job_id": "a1b2c3d4e5f6",
  "message_id": 12,
  "from_agent": "coder_agent",
  "to_agent": "pm_agent",
  "message_type": "clarification_request",
  "topic": "auth_scope",
  "blocking": true,
  "round": 2,
  "status": "resolved",
  "created_at": 1740787200.123,
  "resolved_at": 1740787221.987,
  "content_json": {
    "question": "Do we need OAuth in MVP?"
  }
}
```

Week 2 payload guarantees:

- `from_agent` is always present.
- `to_agent` is always present.
- `message_type` is always present.
- `blocking` is always present.
- `round` is included for runtime-created/resolved/escalated events.

## Runtime Feature Flags (Week 2)

- `AGENT_COMMS_ENABLED` (default: `false`)
- `AGENT_COMMS_MAX_ROUNDS` (default: `8`)
- `AGENT_COMMS_ESCALATE_BLOCKING_ONLY` (default: `true`)
