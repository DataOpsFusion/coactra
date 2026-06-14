"""Graphiti adapters backed by Coactra AI protocols.

Graphiti owns temporal memory extraction. Coactra AI owns model routing,
structured output, and embeddings through LiteLLM/Instructor. These adapters
connect those stable seams without patching Graphiti internals.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterable
from typing import Any

from pydantic import BaseModel

from coactra.memory.backends._errors import MissingExtraError

try:  # pragma: no cover - import path is exercised in integration tests when installed
    from graphiti_core.cross_encoder.client import CrossEncoderClient
    from graphiti_core.embedder.client import EmbedderClient
    from graphiti_core.llm_client.client import LLMClient
    from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, LLMConfig, ModelSize
    from graphiti_core.prompts.models import Message
except ImportError as exc:  # pragma: no cover - optional extra guard
    raise MissingExtraError("graphiti") from exc

EmbeddingFn = Callable[[str], list[float]]


def _coactra_client_cls() -> type[Any]:
    try:
        from coactra.ai import Client
    except ImportError as exc:  # pragma: no cover - optional sibling package guard
        raise MissingExtraError("graphiti-ai") from exc
    return Client


def _coactra_embedding_cls() -> type[Any]:
    try:
        from coactra.ai import LiteLLMEmbedding
    except ImportError as exc:  # pragma: no cover - optional sibling package guard
        raise MissingExtraError("graphiti-ai") from exc
    return LiteLLMEmbedding


def _cosine() -> Callable[[list[float], list[float]], float]:
    try:
        from coactra.ai import cosine
    except ImportError as exc:  # pragma: no cover - optional sibling package guard
        raise MissingExtraError("graphiti-ai") from exc
    return cosine


def _message_text(message: Message) -> str:
    role = getattr(message, "role", "user")
    role_text = getattr(role, "value", role)
    return f"{str(role_text).upper()}:\n{getattr(message, 'content', '')}"


def _messages_prompt(messages: list[Message]) -> str:
    return "\n\n".join(_message_text(message) for message in messages)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _loads_json_object(text: str) -> dict[str, Any]:
    candidate = _strip_json_fence(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Graphiti expected a JSON object from coactra.ai.ask") from None
        parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Graphiti expected a JSON object from coactra.ai.ask")
    return parsed


def _structured_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        if isinstance(dumped, dict):
            return dumped
    raise TypeError("coactra.ai.structured must return a pydantic model or dict")


def _input_text(input_data: Any) -> str:
    if isinstance(input_data, str):
        return input_data
    if isinstance(input_data, Iterable):
        values = list(input_data)
        if all(isinstance(value, str) for value in values):
            return "\n".join(values)
        return " ".join(str(value) for value in values)
    return str(input_data)


def _truncate(vector: list[float], embedding_dim: int | None) -> list[float]:
    return vector[:embedding_dim] if embedding_dim is not None else vector


class GraphitiAIClient(LLMClient):
    """Graphiti ``LLMClient`` implemented with ``coactra.ai.Client``.

    Pass ``ai_client`` to reuse an already-configured Coactra AI client, or pass
    ``model``/``api_base``/``api_key`` and this adapter will build one. ``small_model``
    is used for Graphiti calls that request ``ModelSize.small``.
    """

    def __init__(
        self,
        *,
        ai_client: Any | None = None,
        small_ai_client: Any | None = None,
        model: str | None = None,
        small_model: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        cache: bool = False,
        **client_defaults: Any,
    ) -> None:
        config_model = model or getattr(ai_client, "model", None)
        super().__init__(
            config=LLMConfig(
                api_key=api_key,
                model=config_model,
                base_url=api_base,
                temperature=temperature,
                max_tokens=max_tokens,
                small_model=small_model,
            ),
            cache=cache,
        )
        defaults = dict(client_defaults)
        defaults.setdefault("temperature", temperature)
        need_client_cls = ai_client is None or (small_ai_client is None and small_model is not None)
        client_cls = _coactra_client_cls() if need_client_cls else None
        if ai_client is None:
            if model is None:
                raise ValueError("model is required when ai_client is not supplied")
            ai_client = client_cls(
                model=model,
                api_base=api_base,
                api_key=api_key,
                **defaults,
            )
        if small_ai_client is None and small_model is not None:
            small_ai_client = client_cls(
                model=small_model,
                api_base=api_base,
                api_key=api_key,
                **defaults,
            )
        self._ai_client = ai_client
        self._small_ai_client = small_ai_client

    def _get_provider_type(self) -> str:
        return "coactra.ai"

    def _client_for_size(self, model_size: ModelSize) -> Any:
        if model_size is ModelSize.small and self._small_ai_client is not None:
            return self._small_ai_client
        return self._ai_client

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        client = self._client_for_size(model_size)
        prompt = _messages_prompt(messages)
        if response_model is not None:
            result = await asyncio.to_thread(
                client.structured,
                response_model,
                prompt,
                max_tokens=max_tokens,
            )
            return _structured_to_dict(result)

        text = await asyncio.to_thread(client.ask, prompt, max_tokens=max_tokens)
        return _loads_json_object(text)


class GraphitiEmbeddingClient(EmbedderClient):
    """Graphiti ``EmbedderClient`` backed by any Coactra ``EmbeddingFn``."""

    def __init__(
        self,
        embed: EmbeddingFn | None = None,
        *,
        model: str = "text-embedding-3-small",
        embedding_dim: int | None = None,
        **embedding_defaults: Any,
    ) -> None:
        self._embed = embed or _coactra_embedding_cls()(model=model, **embedding_defaults)
        self._embedding_dim = embedding_dim

    async def create(self, input_data: Any) -> list[float]:
        vector = await asyncio.to_thread(self._embed, _input_text(input_data))
        return _truncate(list(vector), self._embedding_dim)

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        embed_many = getattr(self._embed, "embed_many", None)
        if callable(embed_many):
            vectors = await asyncio.to_thread(embed_many, input_data_list)
        else:
            vectors = await asyncio.gather(
                *(asyncio.to_thread(self._embed, item) for item in input_data_list)
            )
        return [_truncate(list(vector), self._embedding_dim) for vector in vectors]


class GraphitiEmbeddingReranker(CrossEncoderClient):
    """Graphiti reranker backed by embedding cosine similarity.

    This avoids Graphiti's provider-specific default reranker when callers already
    provide a portable Coactra embedding function.
    """

    def __init__(self, embed: EmbeddingFn, *, embedding_dim: int | None = None) -> None:
        self._embed = embed
        self._embedding_dim = embedding_dim
        self._cosine = _cosine()

    async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]:
        if not passages:
            return []
        query_vector = _truncate(
            list(await asyncio.to_thread(self._embed, query)), self._embedding_dim
        )
        embed_many = getattr(self._embed, "embed_many", None)
        if callable(embed_many):
            passage_vectors = await asyncio.to_thread(embed_many, passages)
        else:
            passage_vectors = await asyncio.gather(
                *(asyncio.to_thread(self._embed, passage) for passage in passages)
            )
        scored = [
            (passage, self._cosine(query_vector, _truncate(list(vector), self._embedding_dim)))
            for passage, vector in zip(passages, passage_vectors, strict=False)
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored


def make_graphiti_ai_client(**kwargs: Any) -> GraphitiAIClient:
    """Factory form for composition roots that prefer function injection."""
    return GraphitiAIClient(**kwargs)


def make_graphiti_ai_clients(
    *,
    ai_client: Any | None = None,
    embed: EmbeddingFn | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Return Graphiti constructor kwargs for Coactra-backed LLM/embedding clients."""
    out: dict[str, Any] = {"llm_client": GraphitiAIClient(ai_client=ai_client, **kwargs)}
    if embed is not None:
        out["embedder"] = GraphitiEmbeddingClient(embed=embed)
        out["cross_encoder"] = GraphitiEmbeddingReranker(embed=embed)
    return out
