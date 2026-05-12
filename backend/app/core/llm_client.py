from __future__ import annotations

import asyncio
import json
from typing import Any, Optional, TypeVar

from openai import AsyncOpenAI

from app.core.config import get_settings

T = TypeVar("T")


class LLMClient:
    """Async wrapper around OpenAI-compatible SDK for DeepSeek-V4-Flash.

    Single responsibility: call the LLM and return the parsed result.
    Does NOT know about story logic, character profiles, or any domain concern.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key_effective,
            base_url=settings.deepseek_base_url,
        )
        self._model = settings.deepseek_model
        self._max_retries = 3
        self._timeout = 120.0

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        """Send a chat completion request and return the raw text content."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "timeout": self._timeout,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                return content
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))
        raise last_exc  # type: ignore[misc]

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Send a chat completion and parse the response as JSON."""
        raw = await self.chat(
            messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return json.loads(raw)

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
    ):
        """Stream chat completion chunks as an async generator."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "timeout": self._timeout,
            "stream": True,
        }
        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
