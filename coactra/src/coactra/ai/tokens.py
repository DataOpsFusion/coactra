"""Token-counting seam with a dependency-light default and optional tiktoken adapter."""
from __future__ import annotations

import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenCounter(Protocol):
    def count(self, text: str, *, model: str | None = None) -> int: ...


class ApproximateTokenCounter:
    """Portable estimate for budgeting when a model tokenizer is unavailable."""

    def count(self, text: str, *, model: str | None = None) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text.encode("utf-8")) / 4))


class TiktokenCounter:
    """Exact OpenAI-tokenizer adapter. Install ``coactra-ai[tiktoken]``."""

    def __init__(self, *, default_model: str = "gpt-4o-mini") -> None:
        try:
            import tiktoken
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("TiktokenCounter requires: pip install coactra-ai[tiktoken]") from exc
        self._tiktoken = tiktoken
        self._default_model = default_model

    def count(self, text: str, *, model: str | None = None) -> int:
        encoding = self._tiktoken.encoding_for_model(model or self._default_model)
        return len(encoding.encode(text))


def count_tokens(
    text: str, *, model: str | None = None, counter: TokenCounter | None = None
) -> int:
    """Count tokens through an injected counter or the dependency-light estimate."""
    return (counter or ApproximateTokenCounter()).count(text, model=model)
