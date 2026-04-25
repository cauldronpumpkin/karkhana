from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from openai import APIError, APITimeoutError, AuthenticationError, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from backend.app.config import settings


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    name: str
    base_url: str
    api_key: str
    default_model: str
    configured_models: tuple[str, ...] = ()


class LLMService:
    def __init__(self) -> None:
        self._providers = self._load_providers()
        self.provider = self._normalize_provider(settings.ai_provider)
        self.model = self._default_model_for(self.provider)
        if settings.ai_model:
            self.model = settings.ai_model

    async def chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        stream: bool = True,
        provider: str | None = None,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        selected_provider = self._normalize_provider(provider or self.provider)
        selected_model = model or self._default_model_for(selected_provider)
        client = self._client_for(selected_provider)
        if client is None:
            yield self._missing_key_response(selected_provider)
            return
        try:
            if not stream:
                response = await client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    stream=False,
                )
                content = response.choices[0].message.content or ""
                if content:
                    yield content
                return

            stream_response = await client.chat.completions.create(
                model=selected_model,
                messages=messages,
                stream=True,
            )
            async for chunk in stream_response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except (APIError, APITimeoutError, AuthenticationError) as error:
            raise RuntimeError(f"LLM error: {type(error).__name__}: {error}") from error

    async def chat_completion_sync(
        self,
        messages: list[ChatCompletionMessageParam],
        provider: str | None = None,
        model: str | None = None,
    ) -> str:
        selected_provider = self._normalize_provider(provider or self.provider)
        selected_model = model or self._default_model_for(selected_provider)
        client = self._client_for(selected_provider)
        if client is None:
            return self._missing_key_response(selected_provider)
        try:
            response = await client.chat.completions.create(
                model=selected_model,
                messages=messages,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except (APIError, APITimeoutError, AuthenticationError) as error:
            raise RuntimeError(f"LLM error: {type(error).__name__}: {error}") from error

    async def list_providers(self, discover: bool = True) -> list[dict[str, Any]]:
        providers = []
        for provider in self._providers.values():
            models = list(provider.configured_models)
            source = "configured"
            if discover and provider.api_key:
                discovered = await self._discover_models(provider)
                if discovered:
                    models = discovered
                    source = "discovered"
            providers.append(
                {
                    "id": provider.id,
                    "name": provider.name,
                    "base_url": provider.base_url,
                    "configured": bool(provider.api_key),
                    "default_model": provider.default_model,
                    "models": models,
                    "models_source": source,
                }
            )
        return providers

    def get_provider(self, provider: str | None = None) -> dict[str, str]:
        provider_id = self._normalize_provider(provider or self.provider)
        config = self._providers[provider_id]
        return {
            "provider": config.id,
            "provider_name": config.name,
            "model": self._default_model_for(provider_id),
        }

    def _client_for(self, provider: str) -> AsyncOpenAI | None:
        config = self._providers.get(provider)
        if not config or not config.api_key:
            return None
        return AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)

    def _normalize_provider(self, provider: str) -> str:
        provider_id = (provider or "").strip().lower()
        if provider_id in {"opencode", "opencode-go", "opencode_go"}:
            provider_id = "opencodego"
        if provider_id not in self._providers:
            provider_id = "zai" if "zai" in self._providers else next(iter(self._providers))
        return provider_id

    def _default_model_for(self, provider: str) -> str:
        config = self._providers[provider]
        if provider == self._normalize_provider(settings.ai_provider) and settings.ai_model:
            return settings.ai_model
        return config.default_model

    def _load_providers(self) -> dict[str, ProviderConfig]:
        agent_models = self._load_claude_agent_models()
        opencodego = self._provider_from_agent_models(
            provider_id="opencodego",
            name="OpenCode Go",
            agent_models=agent_models,
            fallback_base_url=settings.opencodego_api_base_url,
            fallback_api_key=settings.opencodego_api_key,
            fallback_model=settings.opencodego_model,
            expected_base_url="opencode.ai/zen/go",
        )
        zai = self._provider_from_agent_models(
            provider_id="zai",
            name="Z.ai Coding Plan",
            agent_models=agent_models,
            fallback_base_url=settings.zai_api_base_url,
            fallback_api_key=settings.zai_api_key,
            fallback_model=settings.zai_model,
            expected_base_url="api.z.ai",
        )
        return {opencodego.id: opencodego, zai.id: zai}

    def _provider_from_agent_models(
        self,
        provider_id: str,
        name: str,
        agent_models: dict[str, dict[str, Any]],
        fallback_base_url: str,
        fallback_api_key: str,
        fallback_model: str,
        expected_base_url: str,
    ) -> ProviderConfig:
        matches: list[tuple[str, dict[str, Any]]] = []
        for model_id, config in agent_models.items():
            base_url = str(config.get("base_url") or "")
            if expected_base_url in base_url:
                matches.append((model_id, config))

        first_config = matches[0][1] if matches else {}
        configured_models = tuple(model_id for model_id, _ in matches)
        return ProviderConfig(
            id=provider_id,
            name=name,
            base_url=str(first_config.get("base_url") or fallback_base_url),
            api_key=str(first_config.get("api_key") or fallback_api_key),
            default_model=fallback_model if fallback_model in configured_models or not configured_models else configured_models[0],
            configured_models=configured_models or (fallback_model,),
        )

    def _load_claude_agent_models(self) -> dict[str, dict[str, Any]]:
        path = Path(settings.claude_settings_path).expanduser()
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        agent_models = payload.get("agentModels", {})
        return agent_models if isinstance(agent_models, dict) else {}

    async def _discover_models(self, provider: ProviderConfig) -> list[str]:
        url = f"{provider.base_url.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {provider.api_key}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []

        raw_models = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(raw_models, list):
            return []
        models: list[str] = []
        for item in raw_models:
            if isinstance(item, dict):
                model_id = item.get("id") or item.get("model") or item.get("name")
            else:
                model_id = str(item)
            if model_id and model_id not in models:
                models.append(str(model_id))
        return models

    def _missing_key_response(self, provider: str = "zai") -> str:
        return (
            f"LLM provider '{provider}' is not configured yet. Set the provider API key "
            "on the backend environment to enable live AI responses."
        )
