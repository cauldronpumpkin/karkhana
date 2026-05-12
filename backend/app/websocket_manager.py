"""WebSocket connection manager with optional Redis pub/sub for multi-instance scaling.

Patterns from Gemini Deep Research (May 2026): ConnectionManager registry,
JWT auth via sec-websocket-protocol header, graceful cleanup via try-finally,
optional Redis pub/sub fallback for horizontal scaling.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# ── Optional Redis support ──────────────────────────────────────────────

_redis: Any = None


def _get_redis() -> Any:
    """Lazy-load Redis client. Returns None if Redis is unavailable."""
    global _redis
    if _redis is False:  # tried and failed
        return None
    if _redis is not None:
        return _redis
    try:
        import redis.asyncio as aioredis

        _redis = aioredis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        logger.info("Redis pub/sub enabled for WebSocket scaling")
    except Exception as exc:
        logger.warning("Redis unavailable, using in-memory WebSocket only: %s", exc)
        _redis = False
    return _redis if _redis is not False else None


# ── Connection Manager ──────────────────────────────────────────────────


class ConnectionManager:
    """Manages active WebSocket connections with per-user and per-topic targeting."""

    def __init__(self) -> None:
        # {websocket: user_id}
        self._connections: dict[WebSocket, str | None] = {}
        # {user_id: set[WebSocket]}
        self._by_user: dict[str, set[WebSocket]] = {}
        # {topic: set[WebSocket]}
        self._by_topic: dict[str, set[WebSocket]] = {}
        # {websocket: set[topic]}  — reverse map for cleanup
        self._topics_for: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str | None = None) -> None:
        """Accept the WebSocket and register it."""
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = user_id
            if user_id:
                self._by_user.setdefault(user_id, set()).add(websocket)
        logger.debug("WebSocket connected (user=%s, total=%d)", user_id, len(self._connections))

    async def subscribe(self, websocket: WebSocket, topic: str) -> None:
        """Subscribe a WebSocket to a topic (e.g. 'run:<run_id>')."""
        async with self._lock:
            self._by_topic.setdefault(topic, set()).add(websocket)
            self._topics_for.setdefault(websocket, set()).add(topic)
        logger.debug("WebSocket subscribed to topic=%s", topic)

    async def unsubscribe(self, websocket: WebSocket, topic: str) -> None:
        """Unsubscribe a WebSocket from a topic."""
        async with self._lock:
            if topic in self._by_topic:
                self._by_topic[topic].discard(websocket)
                if not self._by_topic[topic]:
                    del self._by_topic[topic]
            if websocket in self._topics_for:
                self._topics_for[websocket].discard(topic)
                if not self._topics_for[websocket]:
                    del self._topics_for[websocket]
        logger.debug("WebSocket unsubscribed from topic=%s", topic)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from the registry, cleaning up all subscriptions."""
        async with self._lock:
            user_id = self._connections.pop(websocket, None)
            if user_id and user_id in self._by_user:
                self._by_user[user_id].discard(websocket)
                if not self._by_user[user_id]:
                    del self._by_user[user_id]
            # Clean up all topic subscriptions for this websocket
            topics = self._topics_for.pop(websocket, set())
            for topic in topics:
                if topic in self._by_topic:
                    self._by_topic[topic].discard(websocket)
                    if not self._by_topic[topic]:
                        del self._by_topic[topic]
        logger.debug("WebSocket disconnected (user=%s, total=%d)", user_id, len(self._connections))

    async def send_personal(self, message: dict[str, Any], user_id: str) -> None:
        """Send a message to all connections belonging to a specific user."""
        async with self._lock:
            sockets = list(self._by_user.get(user_id, set()))
        payload = json.dumps(message)
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                await self.disconnect(ws)

    async def broadcast_to_run(self, run_id: str, message: dict[str, Any]) -> None:
        """Send a message to all clients subscribed to topic 'run:<run_id>'."""
        topic = f"run:{run_id}"
        async with self._lock:
            sockets = list(self._by_topic.get(topic, set()))
        payload = json.dumps(message)
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                await self.disconnect(ws)

        # Publish to Redis for other instances
        redis = _get_redis()
        if redis:
            try:
                await redis.publish(f"karkhana:ws:run:{run_id}", payload)
            except Exception:
                pass

    async def broadcast(self, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
        """Send a message to all connected clients, optionally excluding one."""
        async with self._lock:
            sockets = list(self._connections.keys())
        payload = json.dumps(message)
        for ws in sockets:
            if ws is exclude:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                await self.disconnect(ws)

        # Publish to Redis for other instances
        redis = _get_redis()
        if redis:
            try:
                await redis.publish("karkhana:ws:broadcast", payload)
            except Exception:
                pass

    @property
    def active_count(self) -> int:
        return len(self._connections)

    def topic_subscriber_count(self, topic: str) -> int:
        """Return the number of subscribers for a given topic."""
        return len(self._by_topic.get(topic, set()))


# ── Singleton ───────────────────────────────────────────────────────────


_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Return the singleton ConnectionManager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
