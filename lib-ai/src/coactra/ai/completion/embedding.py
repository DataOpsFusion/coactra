"""Default EmbeddingFn over litellm.embedding + numpy cosine."""
from __future__ import annotations

import numpy as np


def cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _litellm_embedding(**kwargs):
    import litellm

    return litellm.embedding(**kwargs)


class LiteLLMEmbedding:
    """Opinionated default EmbeddingFn. Swap by passing any callable to the engine."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model

    def __call__(self, text: str) -> list[float]:
        resp = _litellm_embedding(model=self.model, input=[text])
        return list(resp["data"][0]["embedding"])
