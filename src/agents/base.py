"""Base agent class with LLM client integration."""

import asyncio
from typing import Any
from openai import AsyncOpenAI, APIError


class BaseAgent:
    """Base class for all agents with LLM interaction."""

    def __init__(self, model_name: str = "qwen-3-coder-next"):
        self.model_name = model_name
        self.client = AsyncOpenAI(base_url="http://localhost:1234/v1")
        self.max_retries = 5

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None
    ) -> str:
        """Generate response with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens
                )
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content
                raise ValueError("Empty response from LLM")
            except APIError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2
    ):
        """Generate response with streaming."""
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        async for chunk in response:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
