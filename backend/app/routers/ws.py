"""WebSocket endpoint for real-time updates (job status, chat, notifications).

Auth: JWT token passed via sec-websocket-protocol header during handshake.
Fallback: X-Worker-Token header for worker connections.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

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
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    tokens = [p.strip() for p in protocols.split(",") if p.strip().startswith("jwt.")]
    if tokens:
        token = tokens[0].removeprefix("jwt.")
        try:
            from backend.app.services.auth import decode_token

            payload = decode_token(token)
            return payload.get("sub") or payload.get("user_id")
        except Exception:
            logger.debug("WebSocket JWT auth failed")

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
        except Exception:
            logger.debug("WebSocket worker auth failed")

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

            # Subscribe to topic (in-memory only for now)
            elif msg_type == "subscribe":
                topic = message.get("topic", "")
                logger.debug("Client subscribed to topic: %s", topic)

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


@router.get("/ws/stats")
async def ws_stats() -> dict:
    """Return WebSocket connection statistics (for monitoring)."""
    manager = get_connection_manager()
    return {
        "active_connections": manager.active_count,
    }
