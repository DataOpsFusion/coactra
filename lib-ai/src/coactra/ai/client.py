"""Compatibility import for provider completion helpers."""

from coactra.ai.completion.client import (
    BoundCompleter,
    Client,
    LiteLLMCompleter,
    ask,
    make_completer,
    structured,
)

__all__ = [
    "ask",
    "structured",
    "make_completer",
    "Client",
    "LiteLLMCompleter",
    "BoundCompleter",
]
