"""Swap seams: one Protocol per backend, exactly one default adapter each."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingFn(Protocol):
    def __call__(self, text: str) -> list[float]: ...


@runtime_checkable
class Completer(Protocol):
    def complete(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> str: ...


@runtime_checkable
class ReasoningStore(Protocol):
    """Procedural-memory record store (cosine nearest-neighbour over embeddings).

    Tenant-partitioned.
    """

    def put(self, tenant: str, trace: Any) -> None: ...

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[Any, float]]:
        """Bounded + quality-filtered: <=k traces with quality>=min_quality, (trace, similarity)."""
        ...

    def get(self, tenant: str, trace_id: str) -> Any | None: ...
