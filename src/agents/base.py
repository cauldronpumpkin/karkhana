"""Base agent class with LLM client integration."""

import asyncio
import inspect
import json
import uuid
from typing import Any
from openai import AsyncOpenAI, APIError

from src.config import config
from src.llm.context_manager import ContextManager
from src.llm.tool_calling import parse_fallback_tool_calls


class BaseAgent:
    """Base class for all agents with LLM interaction."""
    
    # Class-level semaphore to cap concurrent LLM requests across all agents.
    _llm_semaphore = asyncio.Semaphore(max(1, int(config.lm_studio.max_concurrency)))

    def __init__(self, model_name: str | None = None, job_id: str | None = None):
        self.model_name = model_name or config.lm_studio.model_name
        self.client = AsyncOpenAI(
            base_url=config.lm_studio.base_url,
            api_key="not-needed",
            timeout=config.lm_studio.timeout,
        )
        self.max_retries = 5
        self.job_id = job_id
        self.stage: str | None = None
        self.context_type = "agent_call"
        self._context_manager = ContextManager.get()

    def set_runtime_context(
        self,
        *,
        job_id: str | None = None,
        stage: str | None = None,
        context_type: str | None = None,
    ) -> None:
        """Set runtime context metadata used by context compaction manager."""
        if job_id is not None:
            self.job_id = job_id
        if stage is not None:
            self.stage = stage
        if context_type is not None:
            self.context_type = context_type

    async def generate(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        context_type: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_handlers: dict[str, Any] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
        max_tool_rounds: int | None = None,
        fallback_tool_parsing: bool | None = None,
    ) -> str:
        """Generate response with retry logic, thread-safe for local LLM."""
        tool_handlers = tool_handlers or {}
        tooling_enabled = bool(tools) and bool(tool_handlers)
        resolved_max_tool_rounds = int(max_tool_rounds or config.tool_calling.max_rounds)
        resolved_fallback_tool_parsing = (
            bool(config.tool_calling.fallback_enabled)
            if fallback_tool_parsing is None
            else bool(fallback_tool_parsing)
        )

        for attempt in range(self.max_retries):
            try:
                prepared_messages = await self._context_manager.prepare_messages(
                    self.job_id,
                    messages,
                    stage=self.stage,
                    context_type=context_type or self.context_type,
                )

                conversation_messages: list[dict[str, Any]] = [dict(m) for m in prepared_messages]
                tool_rounds = 0
                while True:
                    response = await self._chat_completion(
                        messages=conversation_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        tools=tools if tooling_enabled else None,
                        tool_choice=tool_choice if tooling_enabled else None,
                    )

                    if not response.choices or len(response.choices) == 0:
                        raise ValueError("Empty response from LLM")
                    message = response.choices[0].message
                    content = self._normalize_message_content(getattr(message, "content", ""))

                    tool_calls: list[dict[str, Any]] = []
                    if tooling_enabled:
                        tool_calls = self._extract_structured_tool_calls(message)
                        if not tool_calls and resolved_fallback_tool_parsing:
                            tool_calls = parse_fallback_tool_calls(content)

                    if not tooling_enabled or not tool_calls:
                        await self._context_manager.observe_event(
                            self.job_id,
                            "stage_output",
                            {
                                "job_id": self.job_id,
                                "stage": self.stage,
                                "output": content[:2000] if isinstance(content, str) else str(content)[:2000],
                            },
                        )
                        return content

                    if tool_rounds >= resolved_max_tool_rounds:
                        conversation_messages.append(
                            {
                                "role": "system",
                                "content": "Tool round limit reached. Do not call tools again. Return your best final answer now.",
                            }
                        )
                        final_response = await self._chat_completion(
                            messages=conversation_messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        if not final_response.choices or len(final_response.choices) == 0:
                            raise ValueError("Empty response from LLM after tool round limit.")
                        final_content = self._normalize_message_content(final_response.choices[0].message.content)
                        await self._context_manager.observe_event(
                            self.job_id,
                            "stage_output",
                            {
                                "job_id": self.job_id,
                                "stage": self.stage,
                                "output": final_content[:2000] if isinstance(final_content, str) else str(final_content)[:2000],
                            },
                        )
                        return final_content

                    tool_call_messages: list[dict[str, Any]] = []
                    assistant_tool_calls: list[dict[str, Any]] = []
                    for index, call in enumerate(tool_calls):
                        call_id = str(call.get("id") or f"call_{tool_rounds}_{index}_{uuid.uuid4().hex[:6]}")
                        name = str(call.get("name") or "").strip()
                        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
                        if not name:
                            continue
                        await self._context_manager.observe_event(
                            self.job_id,
                            "tool_call",
                            {
                                "job_id": self.job_id,
                                "stage": self.stage,
                                "tool_name": name,
                                "tool_call_id": call_id,
                                "arguments": arguments,
                            },
                        )
                        result_payload = await self._execute_tool_call(
                            tool_name=name,
                            arguments=arguments,
                            tool_handlers=tool_handlers,
                        )
                        await self._context_manager.observe_event(
                            self.job_id,
                            "tool_result",
                            {
                                "job_id": self.job_id,
                                "stage": self.stage,
                                "tool_name": name,
                                "tool_call_id": call_id,
                                "result": str(result_payload)[:1200],
                            },
                        )
                        assistant_tool_calls.append(
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": json.dumps(arguments, ensure_ascii=False),
                                },
                            }
                        )
                        tool_call_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call_id,
                                "name": name,
                                "content": json.dumps(result_payload, ensure_ascii=False),
                            }
                        )

                    if not tool_call_messages:
                        await self._context_manager.observe_event(
                            self.job_id,
                            "stage_output",
                            {
                                "job_id": self.job_id,
                                "stage": self.stage,
                                "output": content[:2000] if isinstance(content, str) else str(content)[:2000],
                            },
                        )
                        return content

                    assistant_tool_call = {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": assistant_tool_calls,
                    }
                    conversation_messages.append(assistant_tool_call)
                    conversation_messages.extend(tool_call_messages)
                    tool_rounds += 1
            except APIError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def generate_stream(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        context_type: str | None = None,
    ):
        """Generate response with streaming, thread-safe for local LLM."""
        prepared_messages = await self._context_manager.prepare_messages(
            self.job_id,
            messages,
            stage=self.stage,
            context_type=context_type or self.context_type,
        )
        async with self._llm_semaphore:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=prepared_messages,
                temperature=temperature,
                stream=True
            )
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    async def _chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int | None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ):
        request: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        if tools:
            request["tools"] = tools
            if tool_choice is not None:
                request["tool_choice"] = tool_choice
        async with self._llm_semaphore:
            return await self.client.chat.completions.create(**request)

    def _normalize_message_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                    continue
                if isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        chunks.append(item["text"])
                        continue
                    if item.get("type") == "text" and isinstance(item.get("content"), str):
                        chunks.append(item["content"])
                        continue
                text = getattr(item, "text", None)
                if isinstance(text, str):
                    chunks.append(text)
            return "\n".join(chunks).strip()
        return str(content)

    def _extract_structured_tool_calls(self, message: Any) -> list[dict[str, Any]]:
        raw_calls = getattr(message, "tool_calls", None)
        if not raw_calls:
            return []

        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(raw_calls):
            raw_dict = self._to_dict(raw)
            call_id = str(raw_dict.get("id") or f"structured_{index}_{uuid.uuid4().hex[:6]}")

            function_data = raw_dict.get("function", {})
            name = None
            arguments: dict[str, Any] = {}
            if isinstance(function_data, dict):
                name = function_data.get("name")
                arguments = self._parse_tool_arguments(function_data.get("arguments"))
            if not name:
                name = raw_dict.get("name")
                arguments = self._parse_tool_arguments(raw_dict.get("arguments"))
            if not isinstance(name, str) or not name.strip():
                continue
            normalized.append(
                {
                    "id": call_id,
                    "name": name.strip(),
                    "arguments": arguments,
                }
            )
        return normalized

    def _parse_tool_arguments(self, raw_args: Any) -> dict[str, Any]:
        if isinstance(raw_args, dict):
            return raw_args
        if raw_args is None:
            return {}
        if isinstance(raw_args, str):
            text = raw_args.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except Exception:
                return {
                    "__parse_error__": "invalid_json_arguments",
                    "_raw": raw_args,
                }
        if isinstance(raw_args, list):
            return {"items": raw_args}
        return {"value": str(raw_args)}

    async def _execute_tool_call(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        tool_handlers: dict[str, Any],
    ) -> dict[str, Any]:
        handler = tool_handlers.get(tool_name)
        if "__parse_error__" in arguments:
            return {
                "ok": False,
                "error": "invalid_tool_arguments_json",
                "tool": tool_name,
                "arguments": arguments,
            }
        if handler is None:
            return {
                "ok": False,
                "error": "unknown_tool",
                "tool": tool_name,
                "arguments": arguments,
            }
        try:
            result = handler(arguments)
            if inspect.isawaitable(result):
                result = await result
            return {
                "ok": True,
                "tool": tool_name,
                "result": result,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": "tool_execution_error",
                "tool": tool_name,
                "message": str(exc),
                "arguments": arguments,
            }

    def _to_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            try:
                dumped = value.model_dump()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
        result: dict[str, Any] = {}
        for attr in ("id", "name", "arguments", "type", "function"):
            attr_value = getattr(value, attr, None)
            if attr_value is None:
                continue
            if attr == "function":
                result[attr] = self._to_dict(attr_value)
            else:
                result[attr] = attr_value
        return result
