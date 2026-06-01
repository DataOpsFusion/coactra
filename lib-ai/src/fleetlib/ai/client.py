"""Wrap shelf. LiteLLM routes; Instructor types. We add nothing but the seam."""
from __future__ import annotations

from typing import Any, TypeVar

import instructor
import litellm
from pydantic import BaseModel

from fleetlib.ai.protocols import Completer

T = TypeVar("T", bound=BaseModel)


class LiteLLMCompleter:
    """Default Completer over litellm.completion."""

    def complete(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        resp = litellm.completion(model=model, messages=messages, **kwargs)
        return resp["choices"][0]["message"]["content"]


def ask(
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
    completer: Completer | None = None,
    **kwargs: Any,
) -> str:
    """Call any model for free-text. completer is swappable; default = LiteLLM."""
    completer = completer or LiteLLMCompleter()
    return completer.complete(model, [{"role": "user", "content": prompt}], **kwargs)


def structured(
    schema: type[T],
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
    **kwargs: Any,
) -> T:
    """Typed output via Instructor (response_model enforcement) over LiteLLM."""
    client = instructor.from_litellm(litellm.completion)
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_model=schema,
        **kwargs,
    )
