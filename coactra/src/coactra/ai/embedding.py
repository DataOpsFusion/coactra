"""Compatibility import for embedding helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["LiteLLMEmbedding", "cosine"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    embedding = import_module("coactra.ai.completion.embedding")
    return getattr(embedding, name)
