from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any, Optional, TypeVar

from openai import AsyncOpenAI, APIStatusError

from app.core.config import get_settings

T = TypeVar("T")


class LLMErrorCode(str, Enum):
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"


class LLMError(Exception):
    """Typed LLM error with classification for proper error handling."""

    def __init__(self, code: LLMErrorCode, message: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.original = original

    @property
    def is_retryable(self) -> bool:
        return self.code not in (LLMErrorCode.QUOTA_EXHAUSTED, LLMErrorCode.UNKNOWN)


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

    @staticmethod
    def _classify_error(exc: Exception) -> LLMErrorCode:
        if isinstance(exc, APIStatusError):
            status = exc.status_code
            if status == 402 or (status == 429 and "quota" in str(exc).lower()):
                return LLMErrorCode.QUOTA_EXHAUSTED
            if status == 429:
                return LLMErrorCode.RATE_LIMITED
        msg = str(exc).lower()
        if "insufficient_quota" in msg or "insufficient balance" in msg:
            return LLMErrorCode.QUOTA_EXHAUSTED
        if "rate_limit" in msg:
            return LLMErrorCode.RATE_LIMITED
        if "timeout" in msg or "connection" in msg or "network" in msg:
            return LLMErrorCode.NETWORK_ERROR
        return LLMErrorCode.UNKNOWN

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

        last_exc: Optional[LLMError] = None
        for attempt in range(self._max_retries):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                return content
            except Exception as exc:
                code = self._classify_error(exc)
                last_exc = LLMError(code, str(exc), exc)
                if not last_exc.is_retryable:
                    break
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code blocks and extra text."""
        text = raw.strip()

        # Strip markdown code blocks (```json ... ``` or ``` ... ```)
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove opening fence (may be ```json or just ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find first { and last } for partial extraction
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract JSON from response: {raw[:300]}...")

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Send a chat completion and parse the response as JSON.

        Does NOT use json_object response_format — DeepSeek supports it
        inconsistently in long conversations. On parse failure, retries
        with a forceful JSON instruction appended to the conversation.
        """
        raw = await self.chat(messages, temperature=temperature)
        try:
            return self._extract_json(raw)
        except ValueError:
            pass

        # Retry: append a forceful instruction to the conversation
        retry_messages = list(messages) + [
            {"role": "assistant", "content": raw[:500]},
            {"role": "user", "content": (
                "You MUST respond with ONLY a JSON object. No markdown, no "
                "explanations, no other text whatsoever. Start with { and end with }. "
                "Follow the JSON format specified in the system prompt EXACTLY."
            )},
        ]
        raw2 = await self.chat(retry_messages, temperature=0.1)
        return self._extract_json(raw2)

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
