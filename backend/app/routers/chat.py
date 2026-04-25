from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from backend.app.repository import Message, get_repository
from backend.app.services.llm import LLMService
from backend.app.services.system_prompts import IDEA_REFINERY_SYSTEM, PHASE_PROMPTS

router = APIRouter(prefix="/api/ideas", tags=["chat"])

llm_service = LLMService()


class ChatMessageRequest(BaseModel):
    message: str
    provider: str | None = None
    model: str | None = None


@router.websocket("/{idea_id}/ws/chat")
async def websocket_chat(websocket: WebSocket, idea_id: str):
    await websocket.accept()
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea:
        await websocket.send_json({"type": "error", "message": f"Idea {idea_id} not found"})
        await websocket.close()
        return
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            user_text = payload.get("message", "").strip()
            provider = payload.get("provider")
            model = payload.get("model")
            if not user_text:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue
            await repo.add_message(Message(idea_id=idea_id, role="user", content=user_text))
            messages = await _build_context(idea_id, idea.current_phase)
            messages.append({"role": "user", "content": user_text})
            assistant_content = ""
            message_id = str(uuid4())
            async for chunk in llm_service.chat_completion(messages, stream=True, provider=provider, model=model):
                assistant_content += chunk
                await websocket.send_json({"type": "chunk", "content": chunk})
            await repo.add_message(Message(id=message_id, idea_id=idea_id, role="assistant", content=assistant_content))
            await websocket.send_json({"type": "done", "message_id": message_id})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


@router.get("/{idea_id}/chat/history")
async def get_chat_history(idea_id: str):
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    messages = await repo.list_messages(idea_id)
    return [
        {
            "id": msg.id,
            "idea_id": msg.idea_id,
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            "metadata": msg.metadata_,
        }
        for msg in messages
    ]


@router.post("/{idea_id}/chat/message")
async def send_chat_message(idea_id: str, body: ChatMessageRequest):
    repo = get_repository()
    idea = await repo.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    await repo.add_message(Message(idea_id=idea_id, role="user", content=body.message))
    messages = await _build_context(idea_id, idea.current_phase)
    messages.append({"role": "user", "content": body.message})
    try:
        assistant_content = ""
        async for chunk in llm_service.chat_completion(
            messages,
            stream=True,
            provider=body.provider,
            model=body.model,
        ):
            assistant_content += chunk
        message_id = str(uuid4())
        await repo.add_message(Message(id=message_id, idea_id=idea_id, role="assistant", content=assistant_content))
        return {"message_id": message_id, "content": assistant_content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _build_context(idea_id: str, phase: str) -> list[ChatCompletionMessageParam]:
    system_prompt = IDEA_REFINERY_SYSTEM
    phase_instruction = PHASE_PROMPTS.get(phase, "")
    if phase_instruction:
        system_prompt += f"\n\nCurrent phase: {phase}. {phase_instruction}"
    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}]
    for msg in await get_repository().list_messages(idea_id):
        messages.append({"role": msg.role, "content": msg.content})
    return messages
