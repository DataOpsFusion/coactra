"""coactra.ai — model-call shelf + reasoning capture-replay.

    import coactra.ai as ai
    ai.ask("hi")                       # call any model (LiteLLM)
    ai.structured(Schema, "...")       # typed output (Instructor)
    eng = ai.ReasoningEngine(store=ai.InMemoryStore(),
                             embed=ai.LiteLLMEmbedding(),
                             reasoner=lambda p: ai.ask(p))
    eng.recall_or_reason("tenant", problem)   # replay or re-reason
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

from coactra._version import distribution_version

# Wrap shelf (LiteLLM + Instructor). Guarded: if those heavy/optional providers
# cannot be imported, the novel reasoning core below still loads and works.
try:
    from coactra.ai.completion.client import (
        Client,
        LiteLLMCompleter,
        ask,
        make_completer,
        structured,
    )

    _WRAP_SHELF = True
except ImportError:  # pragma: no cover - only when litellm/instructor missing
    _WRAP_SHELF = False

    def _missing_wrap_shelf(*args, **kwargs):
        raise ImportError("coactra.ai completion helpers require litellm and instructor")

    class _MissingProviderSDK:
        def __init__(self, *args, **kwargs) -> None:
            _missing_wrap_shelf()

    ask = _missing_wrap_shelf
    structured = _missing_wrap_shelf
    make_completer = _missing_wrap_shelf
    Client = _MissingProviderSDK
    LiteLLMCompleter = _MissingProviderSDK

from coactra.ai.replay.engine import ReasoningEngine
from coactra.ai.replay.gate import AdaptiveGate
from coactra.ai.replay.models import Decision, ReasoningTrace, RecallResult
from coactra.ai.replay.store import InMemoryStore
from coactra.ai.routing import TenantReasoningStoreRouter
from coactra.ai.tokens import ApproximateTokenCounter, TiktokenCounter, TokenCounter, count_tokens

__version__ = distribution_version()

_LAZY_AI_EXPORTS = frozenset({"LiteLLMEmbedding", "cosine"})

__all__ = [
    "__version__",
    "ask",
    "structured",
    "make_completer",
    "Client",
    "LiteLLMCompleter",
    "LiteLLMEmbedding",
    "cosine",
    "ReasoningEngine",
    "AdaptiveGate",
    "InMemoryStore",
    "ReasoningTrace",
    "RecallResult",
    "Decision",
    "TokenCounter",
    "ApproximateTokenCounter",
    "TiktokenCounter",
    "count_tokens",
    "TenantReasoningStoreRouter",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_AI_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    embedding = import_module("coactra.ai.completion.embedding")
    return getattr(embedding, name)
