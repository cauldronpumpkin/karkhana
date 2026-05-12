"""WebSocket endpoint for real-time updates (job status, chat, notifications).

Auth: JWT token passed via sec-websocket-protocol header during handshake.
Fallback: X-Worker-Token header for worker connections.

POST /api/ws/emit — Push endpoint for Karigar workers to emit run-scoped events.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.services.local_workers import LocalWorkerService
from backend.app.websocket_manager import ConnectionManager, get_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def _authenticate(websocket: WebSocket) -> str | None:
    """Extract and verify user/worker identity from WebSocket headers.

    Returns user_id if authenticated, None for anonymous.
    """
    # JWT token via sec-websocket-protocol (used by SvelteKit client)
    # NOTE: ``backend.app.services.auth`` does **not** exist.  JWT auth is a
    # future feature flagged here; any attempt silently degrades to anonymous.
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    tokens = [p.strip() for p in protocols.split(",") if p.strip().startswith("jwt.")]
    if tokens:
        token = tokens[0].removeprefix("jwt.")
        try:
            from backend.app.services.auth import decode_token  # noqa: F811

            payload = decode_token(token)
            return payload.get("sub") or payload.get("user_id")
        except ImportError as exc:
            logger.debug("WebSocket JWT auth unavailable: %s", exc)
        except Exception as exc:
            logger.debug("WebSocket JWT auth failed: %s", exc)

    # Worker token fallback
    worker_token = (
        websocket.headers.get("authorization", "")
        .removeprefix("Bearer ")
        .strip()
    )
    if worker_token:
        try:
            # Extract worker_id from query params or just validate the token
            worker_id = websocket.query_params.get("worker_id", "")
            if worker_id:
                await LocalWorkerService().verify_worker_token(worker_id, worker_token)
                return f"worker:{worker_id}"
        except (PermissionError, ValueError) as exc:
            logger.debug("WebSocket worker auth failed: %s", exc)
        except Exception as exc:
            logger.warning("WebSocket worker auth unexpected error: %s", exc)

    return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time bidirectional communication."""
    manager = get_connection_manager()
    user_id = await _authenticate(websocket)

    await manager.connect(websocket, user_id=user_id)

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "detail": "Invalid JSON"})
                )
                continue

            msg_type = message.get("type", "")
            logger.debug("WebSocket message: type=%s user=%s", msg_type, user_id)

            # Echo / ping
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            # Subscribe to topic
            elif msg_type == "subscribe":
                topic = message.get("topic", "")
                if topic:
                    await manager.subscribe(websocket, topic)
                    logger.debug("Client subscribed to topic: %s", topic)
                    await websocket.send_text(
                        json.dumps({"type": "subscribed", "topic": topic})
                    )

            # Unsubscribe from topic
            elif msg_type == "unsubscribe":
                topic = message.get("topic", "")
                if topic:
                    await manager.unsubscribe(websocket, topic)
                    logger.debug("Client unsubscribed from topic: %s", topic)
                    await websocket.send_text(
                        json.dumps({"type": "unsubscribed", "topic": topic})
                    )

            # Broadcast message to all connected clients
            elif msg_type == "broadcast":
                payload = message.get("payload", {})
                await manager.broadcast(payload, exclude=websocket)

            # Unknown message type — echo back acknowledgment
            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "ack",
                            "original_type": msg_type,
                            "detail": "Message received",
                        }
                    )
                )

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        await manager.disconnect(websocket)


# ── Emit Endpoint (POST, for Karigar workers) ──────────────────────────


class EmitEventRequest(BaseModel):
    """Request body for POST /api/ws/emit."""
    run_id: str
    event_type: str
    payload: dict | None = None


@router.post("/api/ws/emit")
async def emit_event(
    body: EmitEventRequest,
    authorization: str | None = Header(default=None),
    x_worker_id: str | None = Header(default=None, alias="X-Worker-ID"),
) -> dict:
    """Accept events from Karigar workers and broadcast to subscribed WebSocket clients.

    Auth: Worker token via Authorization: Bearer <token> header.
          Worker ID via X-Worker-ID header.

    Broadcasts the event to all WebSocket clients subscribed to topic 'run:<run_id>'.
    """
    token = (authorization or "").removeprefix("Bearer ").strip()
    worker_id = x_worker_id or ""

    if not worker_id:
        raise HTTPException(status_code=400, detail="Missing X-Worker-ID header")

    try:
        await LocalWorkerService().verify_worker_token(worker_id, token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    manager = get_connection_manager()
    message = {
        "type": body.event_type,
        "run_id": body.run_id,
        "payload": body.payload or {},
    }
    await manager.broadcast_to_run(body.run_id, message)

    subscribers = manager.topic_subscriber_count(f"run:{body.run_id}")
    logger.debug(
        "WebSocket event emitted: type=%s run=%s subscribers=%d",
        body.event_type,
        body.run_id,
        subscribers,
    )

    return {
        "status": "broadcast",
        "event_type": body.event_type,
        "run_id": body.run_id,
        "subscribers": subscribers,
    }


@router.get("/ws/stats")
async def ws_stats() -> dict:
    """Return WebSocket connection statistics (for monitoring)."""
    manager = get_connection_manager()
    return {
        "active_connections": manager.active_count,
    }
