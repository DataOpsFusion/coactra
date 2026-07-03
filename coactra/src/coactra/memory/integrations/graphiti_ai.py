"""Graphiti adapters backed by Coactra AI completion helpers.

Graphiti owns temporal memory extraction. Coactra AI owns model routing,
structured output, and provider calls through LiteLLM/Instructor. These adapters
connect that seam without patching Graphiti internals.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from coactra.memory.backends._errors import MissingExtraError

try:  # pragma: no cover - import path is exercised in integration tests when installed
    from graphiti_core.llm_client.client import LLMClient
    from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, LLMConfig, ModelSize
    from graphiti_core.prompts.models import Message
except ImportError as exc:  # pragma: no cover - optional extra guard
    raise MissingExtraError("graphiti") from exc


def _coactra_client_cls() -> type[Any]:
    try:
        from coactra.ai import Client
    except ImportError as exc:  # pragma: no cover - optional sibling package guard
        raise MissingExtraError("graphiti-ai") from exc
    return Client


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
            result = client.structured(response_model, prompt, max_tokens=max_tokens)
            return _structured_to_dict(result)

        text = client.ask(prompt, max_tokens=max_tokens)
        return _loads_json_object(text)


def make_graphiti_ai_client(**kwargs: Any) -> GraphitiAIClient:
    """Factory form for composition roots that prefer function injection."""
    return GraphitiAIClient(**kwargs)


def make_graphiti_ai_clients(
    *,
    ai_client: Any | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Return Graphiti constructor kwargs for the Coactra-backed LLM client."""
    return {"llm_client": GraphitiAIClient(ai_client=ai_client, **kwargs)}
