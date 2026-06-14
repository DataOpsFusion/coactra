"""Default EmbeddingFn over litellm.embedding + numpy cosine."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # annotation only — no runtime dep on replay.models (avoids a cycle)
    from coactra.ai.replay.models import ReasoningTrace


def _require_numpy():
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - base install gate
        from coactra.errors import MissingExtraError

        raise MissingExtraError(
            "embedding helpers require coactra[ai]; install with: pip install coactra[ai]"
        ) from exc
    return np


def cosine(a: list[float], b: list[float]) -> float:
    np = _require_numpy()
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def rank_traces(
    query: list[float],
    candidates: Iterable[ReasoningTrace],
    k: int,
    min_quality: float,
) -> list[tuple[ReasoningTrace, float]]:
    """Quality-filter, cosine-score against ``query``, sort best-first, return the top ``k``.

    The shared ranking semantics for every ReasoningStore: each adapter supplies its own
    candidate traces (in-memory dict, Chroma query, ...); the filter/score/order lives here
    once so a change to ranking can't desync across adapters.
    """
    scored = [
        (trace, cosine(query, trace.embedding))
        for trace in candidates
        if trace.quality >= min_quality
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:k]


def _litellm_embedding(**kwargs):
    import litellm

    return litellm.embedding(**kwargs)


class LiteLLMEmbedding:
    """Default EmbeddingFn over LiteLLM.

    ``model`` plus ``**defaults`` is the embedding equivalent of ``Client``'s
    provider binding: configure base URL, API key, dimensions, or provider-specific
    LiteLLM kwargs once, then pass the callable wherever an ``EmbeddingFn`` is
    accepted.
    """

    def __init__(self, model: str = "text-embedding-3-small", **defaults: Any) -> None:
        self.model = model
        self._defaults = defaults

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        resp = _litellm_embedding(model=self.model, input=list(texts), **self._defaults)
        return [list(item["embedding"]) for item in resp["data"]]

    def __call__(self, text: str) -> list[float]:
        return self.embed_many([text])[0]
