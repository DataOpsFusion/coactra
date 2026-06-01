"""Optional ChromaStore adapter — install with `pip install fleetlib-ai[chroma]`.

Stub: implements the ReasoningStore Protocol shape over a Chroma collection.
Construction fails loudly if chromadb is not installed.
"""
from __future__ import annotations

from typing import Any

from fleetlib.ai.embedding import cosine
from fleetlib.ai.models import ReasoningTrace


class ChromaStore:
    def __init__(self, collection: str = "reasoning", **client_kwargs: Any) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "ChromaStore requires chromadb (the 'chroma' extra): "
                "pip install fleetlib-ai[chroma]"
            ) from exc
        self._client = chromadb.Client(**client_kwargs)
        self._col = self._client.get_or_create_collection(collection)

    def put(self, tenant: str, trace: ReasoningTrace) -> None:
        self._col.upsert(
            ids=[f"{tenant}:{trace.id}"],
            embeddings=[trace.embedding],
            metadatas=[{"tenant": tenant, **trace.model_dump(exclude={"embedding"})}],
        )

    def get(self, tenant: str, trace_id: str) -> ReasoningTrace | None:
        res = self._col.get(ids=[f"{tenant}:{trace_id}"], include=["metadatas", "embeddings"])
        if not res["ids"]:
            return None
        meta = res["metadatas"][0]
        return ReasoningTrace(embedding=res["embeddings"][0], **{k: v for k, v in meta.items() if k != "tenant"})

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[ReasoningTrace, float]]:
        res = self._col.query(query_embeddings=[vector], n_results=k * 4, where={"tenant": tenant})
        out: list[tuple[ReasoningTrace, float]] = []
        for meta, emb in zip(res["metadatas"][0], res["embeddings"][0]):
            t = ReasoningTrace(embedding=emb, **{k2: v for k2, v in meta.items() if k2 != "tenant"})
            if t.quality >= min_quality:
                out.append((t, cosine(vector, emb)))
        out.sort(key=lambda p: p[1], reverse=True)
        return out[:k]
