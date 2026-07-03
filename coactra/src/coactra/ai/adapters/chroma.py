"""Optional ChromaStore adapter - install with `pip install coactra[chroma]`."""

from __future__ import annotations

import json
from typing import Any

from coactra.ai.replay.models import ReasoningTrace
from coactra.ai.replay.store import _rank_traces

_META_JSON = "coactra_meta_json"


def _to_metadata(tenant: str, trace: ReasoningTrace) -> dict[str, str | int | float | bool]:
    """Map a trace into Chroma's scalar-only metadata shape."""
    values = trace.model_dump(exclude={"embedding", "meta"})
    return {
        "tenant": tenant,
        **values,
        _META_JSON: json.dumps(trace.meta, separators=(",", ":"), sort_keys=True),
    }


def _from_metadata(metadata: dict[str, Any], embedding: list[float]) -> ReasoningTrace:
    """Rebuild a trace while tolerating records written before meta JSON was added."""
    values = {key: value for key, value in metadata.items() if key != "tenant"}
    encoded_meta = values.pop(_META_JSON, "{}")
    meta = json.loads(encoded_meta) if isinstance(encoded_meta, str) else {}
    if not isinstance(meta, dict):
        raise ValueError("stored Chroma reasoning metadata must decode to an object")
    return ReasoningTrace(embedding=embedding, meta=meta, **values)


class ChromaStore:
    def __init__(self, collection: str = "reasoning", **client_kwargs: Any) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "ChromaStore requires chromadb (the 'chroma' extra): "
                "pip install coactra[ai][chroma]"
            ) from exc
        self._client = chromadb.Client(**client_kwargs)
        self._col = self._client.get_or_create_collection(collection)

    def put(self, tenant: str, trace: ReasoningTrace) -> None:
        self._col.upsert(
            ids=[f"{tenant}:{trace.id}"],
            embeddings=[trace.embedding],
            metadatas=[_to_metadata(tenant, trace)],
        )

    def get(self, tenant: str, trace_id: str) -> ReasoningTrace | None:
        res = self._col.get(ids=[f"{tenant}:{trace_id}"], include=["metadatas", "embeddings"])
        if not res["ids"]:
            return None
        return _from_metadata(res["metadatas"][0], res["embeddings"][0])

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[ReasoningTrace, float]]:
        # Over-fetch stays adapter-local; ranking/filtering matches InMemoryStore.
        res = self._col.query(
            query_embeddings=[vector],
            n_results=k * 4,
            where={"tenant": tenant},
            include=["metadatas", "embeddings"],
        )
        candidates = [
            _from_metadata(meta, emb)
            for meta, emb in zip(res["metadatas"][0], res["embeddings"][0], strict=False)
        ]
        return _rank_traces(vector, candidates, k, min_quality)
