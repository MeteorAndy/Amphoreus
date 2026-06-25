from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any, Optional, TypeVar

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.core.config import get_settings

T = TypeVar("T")


class LLMErrorCode(str, Enum):
    AUTH_ERROR = "AUTH_ERROR"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    BREAKER_OPEN = "BREAKER_OPEN"
    UNKNOWN = "UNKNOWN"


class LLMError(Exception):
    """Typed LLM error with classification for proper error handling."""

    def __init__(self, code: LLMErrorCode, message: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.original = original

    @property
    def is_retryable(self) -> bool:
        return self.code not in (
            LLMErrorCode.AUTH_ERROR,
            LLMErrorCode.QUOTA_EXHAUSTED,
            LLMErrorCode.PARSE_ERROR,
            LLMErrorCode.UNKNOWN,
        )


class LLMClient:
    """Async wrapper around OpenAI-compatible SDK for DeepSeek-V4-Flash.

    Single responsibility: call the LLM and return the parsed result.
    Does NOT know about story logic, character profiles, or any domain concern.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._timeout = settings.deepseek_timeout
        self._max_retries = max(1, settings.deepseek_max_retries)
        self._http_timeout = httpx.Timeout(
            self._timeout, connect=min(5.0, self._timeout)
        )
        self._api_key = settings.deepseek_api_key_effective
        self._base_url = settings.deepseek_base_url
        self._model = settings.deepseek_model
        self._client: AsyncOpenAI | None = None

    def _ensure_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._api_key:
                raise LLMError(
                    LLMErrorCode.AUTH_ERROR,
                    "DeepSeek API key is not configured. Please set DEEPSEEK_API_KEY "
                    "or configure it in ~/.amphoreus/config.json.",
                )
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._http_timeout,
                max_retries=0,
            )
        return self._client

    @staticmethod
    def _classify_error(exc: Exception) -> LLMErrorCode:
        # Prefer exception TYPE over string matching — the SDK's message text is
        # not a stable contract (e.g. APITimeoutError reads "Request timed out."
        # which does not contain the substring "timeout").
        if isinstance(exc, APITimeoutError):
            return LLMErrorCode.NETWORK_ERROR
        if isinstance(exc, RateLimitError):
            # 429: quota-exhaustion (402-like) vs transient throttling.
            if "quota" in str(exc).lower() or "insufficient" in str(exc).lower():
                return LLMErrorCode.QUOTA_EXHAUSTED
            return LLMErrorCode.RATE_LIMITED
        if isinstance(exc, APIStatusError):
            status = exc.status_code
            if status in (401, 403):
                return LLMErrorCode.AUTH_ERROR
            if status == 402:
                return LLMErrorCode.QUOTA_EXHAUSTED
            if status == 429:
                return LLMErrorCode.RATE_LIMITED
            # 5xx (incl. Cloudflare 502/503/504/524) and 408/409 are transient.
            if status >= 500 or status in (408, 409):
                return LLMErrorCode.NETWORK_ERROR
        if isinstance(exc, APIConnectionError):
            # Base class for connection drops / DNS / read failures.
            return LLMErrorCode.NETWORK_ERROR
        msg = str(exc).lower()
        if (
            "authentication" in msg
            or "invalid api key" in msg
            or "invalid_api_key" in msg
            or "api key" in msg and "invalid" in msg
        ):
            return LLMErrorCode.AUTH_ERROR
        if "insufficient_quota" in msg or "insufficient balance" in msg:
            return LLMErrorCode.QUOTA_EXHAUSTED
        if "rate_limit" in msg:
            return LLMErrorCode.RATE_LIMITED
        if (
            "timeout" in msg
            or "timed out" in msg
            or "connection" in msg
            or "network" in msg
        ):
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
        client = self._ensure_client()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "timeout": self._timeout,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        for attempt in range(self._max_retries):
            try:
                response = await client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as exc:
                await self._handle_retry(exc, attempt)
        raise AssertionError("retry loop exhausted")  # pragma: no cover

    async def _handle_retry(self, exc: Exception, attempt: int) -> None:
        """Sleep before the next attempt, or raise if the error is terminal.

        Raises the wrapped LLMError when the error is non-retryable or the final
        attempt has been used; otherwise sleeps (capped exponential backoff) and
        returns so the caller can retry.
        """
        err = LLMError(self._classify_error(exc), str(exc), exc)
        if not err.is_retryable or attempt >= self._max_retries - 1:
            raise err
        # Capped exponential backoff: 2s, 4s, 8s, ... up to 30s.
        await asyncio.sleep(min(2.0 * (2 ** attempt), 30.0))

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
        inconsistently in long conversations. On a parse miss, re-asks with a
        forceful JSON instruction (up to self._max_retries attempts), lowering
        temperature each round. A persistent miss is raised as a classified
        LLMError(PARSE_ERROR) — NOT a bare ValueError — so callers that guard on
        LLMError (e.g. the pipeline orchestrator) handle it gracefully instead
        of crashing the whole run on a single stochastic bad response.
        """
        convo = list(messages)
        last_raw = ""
        for attempt in range(self._max_retries):
            temp = temperature if attempt == 0 else 0.1
            last_raw = await self.chat(convo, temperature=temp)
            try:
                return self._extract_json(last_raw)
            except ValueError:
                pass
            # Re-ask: show the model its bad output and demand pure JSON.
            convo = list(messages) + [
                {"role": "assistant", "content": last_raw[:500]},
                {"role": "user", "content": (
                    "Your previous reply was not valid JSON. Respond with ONLY a "
                    "JSON object — no markdown, no code fences, no explanations. "
                    "Start with { and end with }. Follow the JSON format specified "
                    "in the system prompt EXACTLY."
                )},
            ]
        raise LLMError(
            LLMErrorCode.PARSE_ERROR,
            f"Could not parse JSON after {self._max_retries} attempts. "
            f"Last response: {last_raw[:300]}",
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
    ):
        """Stream chat completion chunks as an async generator.

        Hardened against the two failure modes that silently hang generation:
        - the initial connect is retried (timeout / 5xx / network) like chat();
        - each chunk is awaited under an idle timeout, so a stream that stalls
          mid-output (a server that stops sending but never closes — the classic
          gateway-524 symptom) raises instead of blocking forever.

        Retries cover only the CONNECT phase. Once bytes have been yielded we
        cannot safely restart (the caller already consumed a partial response),
        so a mid-stream failure surfaces as an LLMError to the caller.
        """
        client = self._ensure_client()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "timeout": self._timeout,
            "stream": True,
        }

        stream = None
        for attempt in range(self._max_retries):
            try:
                stream = await client.chat.completions.create(**kwargs)
                break
            except Exception as exc:
                await self._handle_retry(exc, attempt)
        assert stream is not None  # _handle_retry raised on the last attempt

        iterator = stream.__aiter__()
        while True:
            try:
                chunk = await asyncio.wait_for(iterator.__anext__(), timeout=self._timeout)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError as exc:
                raise LLMError(
                    LLMErrorCode.NETWORK_ERROR,
                    f"Stream stalled: no chunk received within {self._timeout}s",
                    exc,
                ) from exc
            except Exception as exc:
                raise LLMError(self._classify_error(exc), str(exc), exc) from exc
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
