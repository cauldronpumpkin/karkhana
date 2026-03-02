"""FastAPI server with WebSocket for live dashboard + command center."""

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.dynamic_agent import DynamicAgent
from src.agents.ideas_manager import IdeaManager
from src.agents.template_manager import TemplateManager
from src.agents.workflow_manager import WorkflowManager
from src.command_center.models import (
    ApproveJobRequest,
    ChatCommandRequest,
    ContextCompactionConfig,
    CreateJobRequest,
    JobReasoningConfig,
    JobReasoningLaunchOptions,
    JobContextConfig,
    ReasoningConfig,
    ResolveAgentMessageRequest,
)
from src.command_center.service import CommandCenterService
from src.dashboard.event_bus import Event, EventBus
from src.dashboard.models import WSCommand
from src.utils.parser import extract_json


STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Karkhana Dashboard", version="0.2.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
command_center = CommandCenterService.get()
template_manager = TemplateManager()
idea_manager = IdeaManager()
workflow_manager = WorkflowManager()


async def _relay_event(event: Event):
    await manager.broadcast(event.to_dict())


@app.on_event("startup")
async def _register_relay():
    EventBus.get().subscribe(_relay_event)
    await command_center.bootstrap()


@app.on_event("shutdown")
async def _unregister_relay():
    EventBus.get().unsubscribe(_relay_event)


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)

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
    bus = EventBus.get()

    if cmd.action == "approve" and cmd.stage:
        if cmd.job_id:
            await command_center.approve_job(cmd.job_id, stage=cmd.stage, edited_data=cmd.edited_data)
        else:
            bus.approve(cmd.stage, cmd.edited_data)
            await bus.emit("stage_approved", {"stage": cmd.stage})

    elif cmd.action == "rerun" and cmd.stage:
        await bus.emit("rerun_requested", {"stage": cmd.stage, "job_id": cmd.job_id})

    elif cmd.action == "stop" and cmd.job_id:
        await command_center.stop_job(cmd.job_id)

    elif cmd.action == "ping":
        await bus.emit("pong", {})


@app.post("/api/approve/{stage}")
async def approve_stage(stage: str, edited_data: dict[str, Any] | None = None):
    bus = EventBus.get()
    bus.approve(stage, edited_data)
    await bus.emit("stage_approved", {"stage": stage})
    return JSONResponse({"ok": True, "stage": stage})


@app.get("/api/status")
async def pipeline_status():
    bus = EventBus.get()
    return JSONResponse(
        {
            "pending_approvals": bus.pending_approvals,
            "event_count": len(bus.history),
            "active_job_id": command_center.active_job_id,
        }
    )


# Command Center APIs
@app.post("/api/command-center/jobs")
async def create_command_center_job(req: CreateJobRequest):
    job = await command_center.enqueue_job(
        req.idea,
        approval_required=req.approval_required,
        label=req.label,
        reasoning=req.reasoning,
    )
    return JSONResponse(job)


@app.get("/api/command-center/jobs")
async def list_command_center_jobs():
    return JSONResponse(command_center.list_jobs())


@app.get("/api/command-center/jobs/{job_id}")
async def get_command_center_job(job_id: str):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    job["decisions"] = command_center.get_job_decisions(job_id)
    return JSONResponse(job)


@app.get("/api/command-center/jobs/{job_id}/events")
async def get_command_center_job_events(job_id: str):
    return JSONResponse(command_center.get_job_events(job_id))


@app.get("/api/command-center/jobs/{job_id}/logs")
async def get_command_center_job_logs(job_id: str):
    return JSONResponse(command_center.get_job_logs(job_id))


@app.get("/api/command-center/jobs/{job_id}/artifacts")
async def get_command_center_job_artifacts(job_id: str):
    return JSONResponse(command_center.get_job_artifacts(job_id))


@app.get("/api/command-center/jobs/{job_id}/agent-messages")
async def get_command_center_job_agent_messages(job_id: str):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return JSONResponse(command_center.get_agent_messages(job_id))


@app.get("/api/command-center/jobs/{job_id}/agent-messages/pending")
async def get_command_center_job_pending_agent_messages(job_id: str):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return JSONResponse(command_center.get_agent_messages(job_id, pending_only=True))


@app.post("/api/command-center/jobs/{job_id}/agent-messages/{message_id}/resolve")
async def resolve_command_center_job_agent_message(job_id: str, message_id: int, req: ResolveAgentMessageRequest):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    resolved = await command_center.resolve_agent_message(
        job_id,
        message_id,
        decision=req.decision.model_dump(),
    )
    if not resolved:
        return JSONResponse({"error": "Agent message not found"}, status_code=404)
    return JSONResponse({"ok": True, "message": resolved})


@app.post("/api/command-center/jobs/{job_id}/stop")
async def stop_command_center_job(job_id: str):
    ok = await command_center.stop_job(job_id)
    return JSONResponse({"ok": ok})


@app.post("/api/command-center/jobs/{job_id}/approve")
async def approve_command_center_job(job_id: str, req: ApproveJobRequest):
    ok = await command_center.approve_job(job_id, stage=req.stage, edited_data=req.edited_data)
    return JSONResponse({"ok": ok})


@app.post("/api/command-center/chat")
async def command_center_chat(req: ChatCommandRequest):
    response = await command_center.handle_chat(req.message, active_job_id=req.active_job_id)
    return JSONResponse(response.model_dump())


@app.get("/api/command-center/settings/context")
async def get_context_settings():
    cfg = command_center.get_context_defaults()
    return JSONResponse(cfg.model_dump())


@app.get("/api/command-center/settings/reasoning")
async def get_reasoning_settings():
    cfg = command_center.get_reasoning_defaults()
    return JSONResponse(cfg.model_dump())


@app.put("/api/command-center/settings/reasoning")
async def put_reasoning_settings(req: ReasoningConfig):
    cfg = command_center.set_reasoning_defaults(req)
    return JSONResponse(cfg.model_dump())


@app.put("/api/command-center/settings/context")
async def put_context_settings(req: ContextCompactionConfig):
    cfg = command_center.set_context_defaults(req)
    return JSONResponse(cfg.model_dump())


@app.get("/api/command-center/jobs/{job_id}/context-settings")
async def get_job_context_settings(job_id: str):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    cfg = command_center.get_job_context_config(job_id)
    return JSONResponse(cfg.model_dump())


@app.get("/api/command-center/jobs/{job_id}/reasoning-settings")
async def get_job_reasoning_settings(job_id: str):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    cfg = command_center.get_job_reasoning_config(job_id)
    return JSONResponse(cfg.model_dump())


@app.put("/api/command-center/jobs/{job_id}/context-settings")
async def put_job_context_settings(job_id: str, req: JobContextConfig):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    if req.job_id != job_id:
        return JSONResponse({"error": "job_id mismatch"}, status_code=400)
    cfg = command_center.set_job_context_config(
        job_id,
        use_global_defaults=req.use_global_defaults,
        override=req.override,
    )
    return JSONResponse(cfg.model_dump())


@app.put("/api/command-center/jobs/{job_id}/reasoning-settings")
async def put_job_reasoning_settings(job_id: str, req: JobReasoningConfig):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    if req.job_id != job_id:
        return JSONResponse({"error": "job_id mismatch"}, status_code=400)
    cfg = command_center.set_job_reasoning_config(
        job_id,
        use_global_defaults=req.use_global_defaults,
        override=req.override,
        launch_override=req.launch_override,
    )
    return JSONResponse(cfg.model_dump())


@app.get("/api/command-center/jobs/{job_id}/context-state")
async def get_job_context_state(job_id: str):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    state = command_center.get_job_context_state(job_id)
    return JSONResponse(state.model_dump())


@app.get("/api/command-center/jobs/{job_id}/context-compactions")
async def get_job_context_compactions(job_id: str):
    job = command_center.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return JSONResponse(command_center.get_job_context_compactions(job_id))


# Dynamic Agent Templates
class GenerateTemplateRequest(BaseModel):
    role_description: str


@app.post("/api/templates/generate")
async def generate_template(req: GenerateTemplateRequest):
    agent = BaseAgent()
    sys_prompt = (
        "You are an expert system designer who creates instructions for AI agents. "
        "Return ONLY valid JSON with 'name', 'system_prompt' (detailed in Markdown), "
        "and 'user_prompt_template' (must include {input} placeholder)."
    )
    user_prompt = (
        f"Design an AI agent based on this role description:\n\n{req.role_description}\n\n"
        "Make the system prompt highly detailed and authoritative. Ensure the user prompt "
        "template is practical and uses the {input} variable representing exactly what the user provides."
    )

    try:
        response_text = await agent.generate(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        data = extract_json(response_text)
        if not data:
            return JSONResponse({"error": "Failed to parse JSON from AI"}, status_code=500)

        return JSONResponse(
            {
                "name": data.get("name", "Generated Agent"),
                "system_prompt": data.get("system_prompt", "You are a helpful assistant."),
                "user_prompt_template": data.get("user_prompt_template", "{input}"),
            }
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/templates")
async def get_templates():
    return JSONResponse(template_manager.get_all())


@app.post("/api/templates")
async def create_template(template_data: dict[str, Any]):
    return JSONResponse(template_manager.create(template_data))


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    success = template_manager.delete(template_id)
    return JSONResponse({"ok": success})


@app.post("/api/templates/{template_id}/run")
async def run_template(template_id: str, payload: dict[str, Any]):
    template = template_manager.get(template_id)
    if not template:
        return JSONResponse({"error": "Template not found"}, status_code=404)

    bus = EventBus.get()
    stage_name = f"custom_agent_{template_id}"
    await bus.emit("stage_start", {"stage": stage_name, "name": template.get("name")})

    try:
        agent = DynamicAgent(template)
        input_text = payload.get("input", "")
        response = await agent.run({"input": input_text})

        await bus.emit("stage_output", {"stage": stage_name, "output": response})
        await bus.emit("stage_complete", {"stage": stage_name})

        return JSONResponse({"ok": True, "output": response})
    except Exception as exc:
        await bus.emit("error", {"stage": stage_name, "message": str(exc)})
        return JSONResponse({"error": str(exc)}, status_code=500)


# Idea Management
@app.get("/api/ideas")
async def get_ideas():
    return JSONResponse(idea_manager.get_all())


@app.post("/api/ideas")
async def create_idea(data: dict[str, Any]):
    text = data.get("text", "")
    if not text:
        return JSONResponse({"error": "Text is required"}, status_code=400)
    return JSONResponse(idea_manager.create(text))


@app.delete("/api/ideas/{idea_id}")
async def delete_idea(idea_id: str):
    success = idea_manager.delete(idea_id)
    return JSONResponse({"ok": success})


# Workflow Management
@app.get("/api/workflows")
async def get_workflows():
    return JSONResponse(workflow_manager.get_all())


@app.post("/api/workflows")
async def create_workflow(data: dict[str, Any]):
    return JSONResponse(workflow_manager.create(data))


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    success = workflow_manager.delete(workflow_id)
    return JSONResponse({"ok": success})


@app.post("/api/workflows/{workflow_id}/run/{idea_id}")
async def run_custom_workflow(workflow_id: str, idea_id: str):
    workflow = workflow_manager.get(workflow_id)
    idea = idea_manager.get(idea_id)

    if not workflow or not idea:
        return JSONResponse({"error": "Workflow or Idea not found"}, status_code=404)

    bus = EventBus.get()
    bus.clear()

    async def execute_sequence(wf: dict[str, Any], id_obj: dict[str, Any]):
        await bus.emit("build_started", {"idea": id_obj["text"]})

        run_info = {"workflow": wf["name"], "timestamp": 0, "status": "running"}
        idea_manager.add_run(id_obj["id"], run_info)

        try:
            current_input = id_obj["text"]
            for step_id in wf["steps"]:
                template = template_manager.get(step_id)
                if not template:
                    await bus.emit("error", {"message": f"Step {step_id} template not found"})
                    break

                stage_name = f"step_{step_id}"
                await bus.emit("stage_start", {"stage": stage_name, "name": template["name"]})

                agent = DynamicAgent(template)
                response = await agent.run({"input": current_input})

                await bus.emit("stage_output", {"stage": stage_name, "output": response})
                await bus.emit("stage_complete", {"stage": stage_name})
                current_input = response

            await bus.emit("build_complete", {})
        except Exception as exc:
            await bus.emit("error", {"message": str(exc)})

    asyncio.create_task(execute_sequence(workflow, idea))
    return JSONResponse({"ok": True, "message": "Custom workflow execution started"})


# Backward-compatible pipeline control
class BuildRequest(BaseModel):
    idea: str
    approval_required: bool = False
    reasoning: JobReasoningLaunchOptions | None = None


@app.post("/api/build")
async def start_build(req: BuildRequest):
    job = await command_center.enqueue_job(
        req.idea,
        approval_required=req.approval_required,
        reasoning=req.reasoning,
    )
    return JSONResponse({"ok": True, "message": "Build pipeline queued", "job_id": job["id"]})


@app.post("/api/build/stop")
async def stop_build():
    active = command_center.active_job_id
    if not active:
        return JSONResponse({"ok": False, "message": "No active pipeline to stop"})

    ok = await command_center.stop_job(active)
    if ok:
        await EventBus.get().emit("error", {"job_id": active, "message": "Pipeline kill signal sent."})
    return JSONResponse({"ok": ok, "message": "Pipeline stopped" if ok else "Failed to stop pipeline"})
