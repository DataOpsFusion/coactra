"""coactra.ai — model-call shelf + reasoning capture-replay.

    import coactra.ai as ai
    ai.ask("hi")                       # call any model (LiteLLM)
    ai.structured(Schema, "...")       # typed output (Instructor)
    eng = ai.ReasoningEngine(store=ai.InMemoryStore(),
                             embed=ai.LiteLLMEmbedding(),
                             reasoner=lambda p: ai.ask(p))
    eng.recall_or_reason("tenant", problem)   # replay or re-reason
"""
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

from coactra.ai.completion.embedding import LiteLLMEmbedding, cosine
from coactra.ai.replay.engine import ReasoningEngine
from coactra.ai.replay.gate import AdaptiveGate
from coactra.ai.replay.models import Decision, ReasoningTrace, RecallResult
from coactra.ai.replay.store import InMemoryStore

__version__ = "0.2.0"

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
]
