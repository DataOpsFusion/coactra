"""fleetlib.ai — model-call shelf + reasoning capture-replay.

    import fleetlib.ai as ai
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
    from fleetlib.ai.client import (
        Client,
        LiteLLMCompleter,
        ask,
        make_completer,
        structured,
    )

    _WRAP_SHELF = True
except ImportError:  # pragma: no cover - only when litellm/instructor missing
    _WRAP_SHELF = False

from fleetlib.ai.embedding import LiteLLMEmbedding, cosine
from fleetlib.ai.engine import ReasoningEngine
from fleetlib.ai.gate import AdaptiveGate
from fleetlib.ai.models import Decision, ReasoningTrace, RecallResult
from fleetlib.ai.store import InMemoryStore

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
