from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core.api_keys import KeyManager


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class LLMClient(ABC):
    """Abstract LLM provider client.

    Every provider implementation must subclass this ABC so that callers
    remain decoupled from the concrete SDK.  The constructor contract is
    ``client = SomeClient(api_key=..., **extra_kwargs)`` — the factory
    function relies on this signature.
    """

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        self.api_key = api_key

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request and return the response text."""
        ...

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> List[List[float]]:
        """Return embedding vectors for a list of input strings."""
        ...


# ---------------------------------------------------------------------------
# Concrete: DeepSeek (OpenAI-compatible)
# ---------------------------------------------------------------------------


class DeepSeekClient(LLMClient):
    """LLM client backed by the DeepSeek API (OpenAI-compatible SDK)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        default_model: str = "deepseek-chat",
        default_embed_model: str = "deepseek-embed",
    ) -> None:
        super().__init__(api_key)
        self.base_url = base_url
        self.default_model = default_model
        self.default_embed_model = default_embed_model
        self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> List[List[float]]:
        response = await self._client.embeddings.create(
            model=model or self.default_embed_model,
            input=texts,
            **kwargs,
        )
        return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_PROVIDER_CLIENTS: Dict[str, type[LLMClient]] = {
    "deepseek": DeepSeekClient,
}


def create_llm_client(
    provider: str = "deepseek",
    api_key: Optional[str] = None,
    km: Optional[KeyManager] = None,
    **overrides: Any,
) -> LLMClient:
    """Build and return an :class:`LLMClient` for the named provider.

    Resolution order for the API key:
    1. Explicit *api_key* argument
    2. :class:`KeyManager` lookup
    3. :exc:`ValueError`

    Extra keyword arguments are forwarded to the client constructor (e.g.
    *base_url*, *default_model*).
    """
    client_cls = _PROVIDER_CLIENTS.get(provider)
    if client_cls is None:
        supported = ", ".join(sorted(_PROVIDER_CLIENTS))
        raise ValueError(
            f"Unsupported provider {provider!r}. Supported: {supported}"
        )

    resolved_key = api_key
    if resolved_key is None:
        key_mgr = km or KeyManager()
        resolved_key = key_mgr.get_key(provider)
    if not resolved_key:
        raise ValueError(
            f"No API key available for provider {provider!r}. "
            "Use KeyManager to store a key first."
        )

    return client_cls(api_key=resolved_key, **overrides)


def register_provider(name: str, client_class: type[LLMClient]) -> None:
    """Register a custom LLM client class for *name*.

    Framework-level extensibility: third-party modules can call this to
    add new provider backends.
    """
    if not issubclass(client_class, LLMClient):
        raise TypeError(f"{client_class.__name__} must subclass LLMClient")
    _PROVIDER_CLIENTS[name] = client_class


def _unregister_provider(name: str) -> None:
    """Remove a previously registered provider (test helper)."""
    _PROVIDER_CLIENTS.pop(name, None)
