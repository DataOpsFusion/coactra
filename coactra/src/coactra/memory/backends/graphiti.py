"""GraphitiBackend — wraps ``graphiti_core.Graphiti`` (natively async).

graphiti builds a temporal knowledge graph from episodes and recalls relationship
"facts". This adapter maps ``Scope`` onto graphiti's ``group_id`` namespace via its
collision-resistant ``Scope.key`` (tenant always first, so isolation holds; injective,
so distinct scopes never collide), calls the native async
API, and maps graphiti's ``EntityEdge`` objects into plain ``Recollection``s. No
graphiti type ever crosses the boundary.

Note the API asymmetry (verified against graphiti_core): ``add_episode`` takes
``group_id`` (singular str); ``search`` takes ``group_ids`` (list) and ``num_results``.

``graphiti_core`` imports lazily — only ``MissingExtraError`` is raised when a backend
is constructed without the extra.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from coactra.memory.backends._errors import MissingExtraError
from coactra.memory.backends.base import event_text
from coactra.memory.capabilities import Capability
from coactra.memory.export import ExportReport
from coactra.memory.types import MemoryEvent, Recollection, Scope

_SOURCE = "graphiti"
_CAPS = {
    Capability.STORE,
    Capability.GRAPH_EDGES,
    Capability.TEMPORAL,
    Capability.PROVENANCE,
}


def _group_id(scope: Scope) -> str:
    """Map Scope → a graphiti-LEGAL, injective group_id.

    graphiti validates ``group_id`` against ``[A-Za-z0-9_-]`` only. The canonical
    ``Scope.key`` uses ':' separators and '*' placeholders — both ILLEGAL there. We
    hex-encode the key: the result is legal AND injective (distinct scopes → distinct
    ids), so tenant isolation is preserved. ``Scope`` still forbids ':' / '*' / empty
    in its fields, keeping ``key`` collision-resistant before encoding.
    """
    return "fl" + scope.key.encode("utf-8").hex()


def _edge_to_recollection(edge: Any, score: float) -> Recollection:
    """Map a graphiti EntityEdge → Recollection. Reads only documented attributes."""
    when = getattr(edge, "valid_at", None)
    return Recollection(
        text=str(getattr(edge, "fact", "")),
        score=score,
        source_id=str(getattr(edge, "uuid", "")),
        when=when if isinstance(when, datetime) else None,
        metadata={
            "source_backend": _SOURCE,
            "group_id": getattr(edge, "group_id", None),
        },
    )


def _normalize_extracted_entities_response(
    response: dict[str, Any], response_model: type[Any] | None
) -> dict[str, Any]:
    """Normalize common OpenAI-compatible extraction variants to Graphiti's schema.

    Graphiti validates entity extraction with an ``ExtractedEntities`` pydantic model
    whose required field is ``extracted_entities``. Some OpenAI-compatible providers
    return the shorter ``entities`` key even when given the JSON schema. Accept that
    provider variant at the Coactra boundary instead of letting all memory writes fail.
    """
    if response_model is None or getattr(response_model, "__name__", "") != "ExtractedEntities":
        return response
    if "extracted_entities" in response or "entities" not in response:
        return response

    entities = response.get("entities")
    extracted: list[dict[str, Any]] = []
    if isinstance(entities, dict):
        for entity_items in entities.values():
            if not isinstance(entity_items, list):
                entity_items = [entity_items]
            for item in entity_items:
                normalized = _normalize_entity_item(item)
                if normalized is not None:
                    extracted.append(normalized)
    elif isinstance(entities, list):
        for item in entities:
            normalized = _normalize_entity_item(item)
            if normalized is not None:
                extracted.append(normalized)
    else:
        normalized = _normalize_entity_item(entities)
        if normalized is not None:
            extracted.append(normalized)
    return {**response, "extracted_entities": extracted}


def _normalize_entity_item(item: Any) -> dict[str, Any] | None:
    if isinstance(item, dict):
        name = item.get("name", item.get("text", item.get("entity", "")))
        if not name:
            return None
        out = dict(item)
        out["name"] = str(name)
        out.setdefault("entity_type_id", 0)
        return out
    if item is None:
        return None
    name = str(item)
    return {"name": name, "entity_type_id": 0} if name else None


_NORMALIZED_FLAG = "_coactra_entities_normalized"


def _patch_generate_response(client: Any) -> Any:
    """Make a graphiti LLMClient normalize provider JSON-key drift
    (``entities`` → ``extracted_entities``) BEFORE Graphiti validates extraction.

    Patches the INSTANCE's ``generate_response`` in place instead of wrapping the
    client in a proxy. Graphiti's ``GraphitiClients`` model validates
    ``isinstance(llm_client, LLMClient)`` at construction, so the object must stay a
    real graphiti ``LLMClient`` subclass — a proxy fails that check. Idempotent: a
    re-patched client is returned unchanged.
    """
    if client is None or getattr(client, _NORMALIZED_FLAG, False):
        return client
    original = client.generate_response

    async def _normalizing_generate_response(*args: Any, **kwargs: Any) -> dict[str, Any]:
        response = await original(*args, **kwargs)
        response_model = kwargs.get("response_model")
        if response_model is None and len(args) > 1:
            response_model = args[1]
        return _normalize_extracted_entities_response(response, response_model)

    client.generate_response = _normalizing_generate_response
    setattr(client, _NORMALIZED_FLAG, True)
    return client


def _graphiti_client_kwargs(
    *,
    llm_client: Any | None,
    embedder: Any | None,
    cross_encoder: Any | None,
    configured_llm: Any | None,
    configured_embedder: Any | None,
    configured_cross_encoder: Any | None,
) -> dict[str, Any]:
    """Select explicit Graphiti clients first, falling back to configured clients.

    Explicit native clients are a public injection seam. They must pass through
    untouched so callers can provide their own Graphiti LLMClient implementation
    instead of receiving a Coactra-side monkey patch.
    """
    graphiti_kwargs: dict[str, Any] = {}
    for name, explicit, configured in (
        ("llm_client", llm_client, configured_llm),
        ("embedder", embedder, configured_embedder),
        ("cross_encoder", cross_encoder, configured_cross_encoder),
    ):
        selected = explicit if explicit is not None else configured
        if selected is not None:
            graphiti_kwargs[name] = selected
    return graphiti_kwargs


def _openai_compatible_clients(
    *,
    llm_provider: str,
    llm_api_key: str | None,
    llm_model: str | None,
    llm_base_url: str | None,
    embedder_api_key: str | None,
    embedder_model: str | None,
    embedder_base_url: str | None,
    embedding_dim: int | None,
) -> tuple[Any | None, Any | None, Any | None]:
    """Build Graphiti's official OpenAI-compatible clients when explicitly configured."""
    if llm_provider not in {"openai", "openai_generic"}:
        raise ValueError("llm_provider must be 'openai' or 'openai_generic'")
    llm_configured = any(value is not None for value in (llm_api_key, llm_model, llm_base_url))
    embedder_configured = any(
        value is not None
        for value in (
            embedder_api_key,
            embedder_model,
            embedder_base_url,
            embedding_dim,
        )
    )
    if not llm_configured and not embedder_configured:
        return None, None, None
    try:
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_client import OpenAIClient
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    except ImportError as exc:  # pragma: no cover - ctor already guards the extra
        raise MissingExtraError("graphiti") from exc

    llm_client = None
    cross_encoder = None
    if llm_configured:
        config = LLMConfig(api_key=llm_api_key, model=llm_model, base_url=llm_base_url)
        client_cls = OpenAIClient if llm_provider == "openai" else OpenAIGenericClient
        llm_client = client_cls(config=config)
        if llm_provider == "openai_generic":
            llm_client = _patch_generate_response(llm_client)
        cross_encoder = OpenAIRerankerClient(config=config, client=llm_client.client)

    embedder = None
    if embedder_configured:
        embedder_kwargs: dict[str, Any] = {}
        if embedder_api_key is not None:
            embedder_kwargs["api_key"] = embedder_api_key
        if embedder_model is not None:
            embedder_kwargs["embedding_model"] = embedder_model
        if embedder_base_url is not None:
            embedder_kwargs["base_url"] = embedder_base_url
        if embedding_dim is not None:
            embedder_kwargs["embedding_dim"] = embedding_dim
        embedder = OpenAIEmbedder(config=OpenAIEmbedderConfig(**embedder_kwargs))
    return llm_client, embedder, cross_encoder


class GraphitiBackend:
    """Adapter over ``graphiti_core.Graphiti``.

    Preferred portable model seams are ``ai_client=coactra.ai.Client(...)`` and
    ``embed=coactra.ai.LiteLLMEmbedding(...)``. Native Graphiti clients remain
    injectable via ``llm_client``/``embedder``/``cross_encoder`` for advanced use.
    """

    declared_capabilities = set(_CAPS)

    def __init__(
        self,
        *,
        client: Any | None = None,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        llm_client: Any | None = None,
        ai_client: Any | None = None,
        embedder: Any | None = None,
        embed: Any | None = None,
        cross_encoder: Any | None = None,
        llm_provider: str = "openai",
        llm_api_key: str | None = None,
        llm_model: str | None = None,
        llm_base_url: str | None = None,
        embedder_api_key: str | None = None,
        embedder_model: str | None = None,
        embedder_base_url: str | None = None,
        embedding_dim: int | None = None,
    ) -> None:
        if client is not None:
            self._client = client
            return
        if ai_client is not None and llm_client is not None:
            raise ValueError("pass either ai_client or llm_client, not both")
        if embed is not None and embedder is not None:
            raise ValueError("pass either embed or embedder, not both")
        try:
            from graphiti_core import Graphiti  # noqa: PLC0415  (lazy: optional extra)
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise MissingExtraError("graphiti") from exc
        if ai_client is not None:
            from coactra.memory.integrations import GraphitiAIClient

            llm_client = GraphitiAIClient(ai_client=ai_client)
        if embed is not None:
            from coactra.memory.integrations import (
                GraphitiEmbeddingClient,
                GraphitiEmbeddingReranker,
            )

            embedder = GraphitiEmbeddingClient(embed=embed, embedding_dim=embedding_dim)
            if cross_encoder is None:
                cross_encoder = GraphitiEmbeddingReranker(embed=embed, embedding_dim=embedding_dim)
        needs_configured_llm = llm_client is None or cross_encoder is None
        needs_configured_embedder = embedder is None
        configured_llm, configured_embedder, configured_cross_encoder = _openai_compatible_clients(
            llm_provider=llm_provider,
            llm_api_key=llm_api_key if needs_configured_llm else None,
            llm_model=llm_model if needs_configured_llm else None,
            llm_base_url=llm_base_url if needs_configured_llm else None,
            embedder_api_key=embedder_api_key if needs_configured_embedder else None,
            embedder_model=embedder_model if needs_configured_embedder else None,
            embedder_base_url=embedder_base_url if needs_configured_embedder else None,
            embedding_dim=embedding_dim if needs_configured_embedder else None,
        )
        graphiti_kwargs = _graphiti_client_kwargs(
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=cross_encoder,
            configured_llm=configured_llm,
            configured_embedder=configured_embedder,
            configured_cross_encoder=configured_cross_encoder,
        )
        self._client = Graphiti(uri, user, password, **graphiti_kwargs)

    async def capabilities(self) -> set[Capability]:
        return set(_CAPS)

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        gid = _group_id(scope)
        now = datetime.now(UTC)
        for i, event in enumerate(events):
            text = event_text(event)
            if not text:
                continue
            await self._client.add_episode(
                name=f"{gid}:{now.timestamp()}:{i}",
                episode_body=text,
                source_description="coactra.memory",
                reference_time=now,
                group_id=gid,
            )

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        edges = await self._client.search(
            query=query,
            group_ids=[_group_id(scope)],
            num_results=k,
        )
        # graphiti returns a relevance-ranked list with no per-edge score; synthesize a
        # descending positional score so ordering is preserved through the boundary.
        n = len(edges)
        return [
            _edge_to_recollection(edge, score=(n - i) / n if n else 0.0)
            for i, edge in enumerate(edges)
        ]

    async def dump(self, scope: Scope) -> list[Recollection]:
        # graphiti has no scope-wide "dump everything"; the broad-recall path is the
        # closest honest approximation for export. Empty query → engine default search.
        edges = await self._client.search(query="", group_ids=[_group_id(scope)])
        return [_edge_to_recollection(edge, score=0.0) for edge in edges]

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        gid = _group_id(scope)
        now = datetime.now(UTC)
        written = 0
        for i, item in enumerate(items):
            if not item.text:
                continue
            await self._client.add_episode(
                name=f"{gid}:ingest:{now.timestamp()}:{i}",
                episode_body=item.text,
                source_description="coactra.memory:export",
                reference_time=now,
                group_id=gid,
            )
            written += 1
        return ExportReport.from_ingest(self, transferred=written)
