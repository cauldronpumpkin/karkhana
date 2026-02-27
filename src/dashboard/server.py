"""FastAPI server with WebSocket for the live dashboard."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.dashboard.event_bus import Event, EventBus
from src.dashboard.models import WSCommand

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Karkhana Dashboard", version="0.1.0")

# Mount static assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Connection manager ─────────────────────────────────────────


class ConnectionManager:
    """Track active WebSocket connections."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active = [c for c in self.active if c is not ws]

    async def broadcast(self, data: dict[str, Any]):
        """Send JSON to every connected client."""
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── EventBus → WebSocket bridge ────────────────────────────────


async def _relay_event(event: Event):
    """Forward every EventBus event to all WS clients."""
    await manager.broadcast(event.to_dict())


# Register the relay when the server starts
@app.on_event("startup")
async def _register_relay():
    EventBus.get().subscribe(_relay_event)


@app.on_event("shutdown")
async def _unregister_relay():
    EventBus.get().unsubscribe(_relay_event)


# ── Routes ─────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dashboard HTML."""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Bidirectional WebSocket: stream events + receive commands."""
    await manager.connect(ws)

    # Send event history so a late-joining client catches up
    bus = EventBus.get()
    for past_event in bus.history:
        try:
            await ws.send_json(past_event.to_dict())
        except Exception:
            break

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                cmd = WSCommand.model_validate(data)
                await _handle_command(cmd)
            except Exception as exc:
                await ws.send_json({"type": "error", "payload": {"message": str(exc)}, "timestamp": 0})
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def _handle_command(cmd: WSCommand):
    """Process an incoming command from the dashboard."""
    bus = EventBus.get()

    if cmd.action == "approve" and cmd.stage:
        bus.approve(cmd.stage, cmd.edited_data)
        await bus.emit("stage_approved", {"stage": cmd.stage})

    elif cmd.action == "rerun" and cmd.stage:
        await bus.emit("rerun_requested", {"stage": cmd.stage})

    elif cmd.action == "ping":
        await bus.emit("pong", {})


# ── REST fallbacks ─────────────────────────────────────────────


@app.post("/api/approve/{stage}")
async def approve_stage(stage: str, edited_data: dict[str, Any] | None = None):
    bus = EventBus.get()
    bus.approve(stage, edited_data)
    await bus.emit("stage_approved", {"stage": stage})
    return JSONResponse({"ok": True, "stage": stage})


@app.get("/api/status")
async def pipeline_status():
    bus = EventBus.get()
    return JSONResponse({
        "pending_approvals": bus.pending_approvals,
        "event_count": len(bus.history),
    })
