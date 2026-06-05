"""GraphitiBackend unit tests with a MOCKED graphiti client.

Proves: (1) native-async engine calls + group_id mapping (singular on add_episode,
plural group_ids on search), (2) EntityEdge → Recollection mapping, (3) NO graphiti
type leaks across the boundary (sentinel-edge proof).
"""

from datetime import datetime, timezone

import pytest

from coactra.memory import Recollection, Scope
from coactra.memory.backends.graphiti import (
    _NORMALIZED_FLAG,
    GraphitiBackend,
    _graphiti_client_kwargs,
    _group_id,
    _normalize_extracted_entities_response,
    _openai_compatible_clients,
    _patch_generate_response,
)


class FakeEdge:
    """Stand-in for graphiti_core EntityEdge — must NEVER cross the boundary."""

    def __init__(self, fact, uuid, valid_at=None, group_id=None):
        self.fact = fact
        self.uuid = uuid
        self.valid_at = valid_at
        self.group_id = group_id


class ExtractedEntities:
    pass


class FakeLLMClient:
    def __init__(self, response):
        self.response = response

    async def generate_response(self, *args, **kwargs):
        return self.response


class FakeGraphiti:
    """Stand-in for graphiti_core.Graphiti. Records async calls; returns FakeEdges."""

    def __init__(self):
        self.add_calls = []
        self.search_calls = []
        self._edges = []

    async def add_episode(self, **kwargs):
        self.add_calls.append(kwargs)

    async def search(self, query, group_ids=None, num_results=None, **kwargs):
        self.search_calls.append(
            {"query": query, "group_ids": group_ids, "num_results": num_results}
        )
        return list(self._edges)


SCOPE = Scope(tenant="acme", agent="builder")


def test_normalize_extracted_entities_accepts_provider_entities_list():
    out = _normalize_extracted_entities_response(
        {"entities": [{"name": "Harbor"}, {"text": "Neo4j"}, "Graphiti"]},
        ExtractedEntities,
    )

    assert out["extracted_entities"] == [
        {"name": "Harbor", "entity_type_id": 0},
        {"text": "Neo4j", "name": "Neo4j", "entity_type_id": 0},
        {"name": "Graphiti", "entity_type_id": 0},
    ]


def test_normalize_extracted_entities_accepts_provider_entities_dict():
    out = _normalize_extracted_entities_response(
        {"entities": {"Service": ["Harbor"], "Database": [{"text": "Neo4j"}]}},
        ExtractedEntities,
    )

    assert out["extracted_entities"] == [
        {"name": "Harbor", "entity_type_id": 0},
        {"text": "Neo4j", "name": "Neo4j", "entity_type_id": 0},
    ]


async def test_patch_generate_response_fixes_extracted_entities_response():
    client = _patch_generate_response(FakeLLMClient({"entities": ["Harbor"]}))

    out = await client.generate_response([], response_model=ExtractedEntities)

    assert out["extracted_entities"] == [{"name": "Harbor", "entity_type_id": 0}]
    assert getattr(client, _NORMALIZED_FLAG) is True


def test_explicit_graphiti_llm_client_is_not_patched():
    explicit = FakeLLMClient({"entities": ["Explicit"]})
    configured = _patch_generate_response(FakeLLMClient({"entities": ["Configured"]}))

    kwargs = _graphiti_client_kwargs(
        llm_client=explicit,
        embedder=None,
        cross_encoder=None,
        configured_llm=configured,
        configured_embedder=None,
        configured_cross_encoder=None,
    )

    assert kwargs == {"llm_client": explicit}
    assert getattr(configured, _NORMALIZED_FLAG) is True
    assert not getattr(explicit, _NORMALIZED_FLAG, False)


async def test_remember_calls_add_episode_with_singular_group_id():
    fake = FakeGraphiti()
    be = GraphitiBackend(client=fake)
    await be.remember(["A depends on B"], SCOPE)

    assert len(fake.add_calls) == 1
    call = fake.add_calls[0]
    assert call["episode_body"] == "A depends on B"
    # tenant ALWAYS leads the group_id (isolation); fixed 3-slot injective key,
    # singular on add_episode.
    assert call["group_id"] == _group_id(SCOPE)
    assert "group_ids" not in call


async def test_recall_calls_search_with_plural_group_ids_and_num_results():
    fake = FakeGraphiti()
    valid = datetime(2026, 1, 2, tzinfo=timezone.utc)
    fake._edges = [
        FakeEdge("A depends on B", "uuid-1", valid_at=valid, group_id=_group_id(SCOPE)),
        FakeEdge("B owns C", "uuid-2", group_id=_group_id(SCOPE)),
    ]
    be = GraphitiBackend(client=fake)
    out = await be.recall("dependencies", SCOPE, k=5)

    call = fake.search_calls[0]
    assert call["query"] == "dependencies"
    assert call["group_ids"] == [_group_id(SCOPE)]  # plural list on search
    assert call["num_results"] == 5

    assert len(out) == 2
    assert all(isinstance(r, Recollection) for r in out)
    assert out[0].text == "A depends on B"
    assert out[0].source_id == "uuid-1"
    assert out[0].when == valid
    assert out[0].metadata["source_backend"] == "graphiti"
    # ranked descending → first edge scores higher than the second.
    assert out[0].score > out[1].score


async def test_dump_searches_scope_group_and_maps_results():
    fake = FakeGraphiti()
    fake._edges = [FakeEdge("A depends on B", "u1", group_id=_group_id(SCOPE))]
    be = GraphitiBackend(client=fake)
    out = await be.dump(SCOPE)

    call = fake.search_calls[0]
    assert call["group_ids"] == [_group_id(SCOPE)]  # tenant leads the group key
    assert [r.text for r in out] == ["A depends on B"]
    assert all(isinstance(r, Recollection) for r in out)
    assert out[0].metadata["source_backend"] == "graphiti"


async def test_ingest_adds_episodes_and_reports_transferred():
    fake = FakeGraphiti()
    be = GraphitiBackend(client=fake)
    report = await be.ingest(
        [Recollection(text="ported edge"), Recollection(text="")], SCOPE
    )
    # empty-text recollection is skipped; one episode written under the scope group_id.
    assert len(fake.add_calls) == 1
    assert fake.add_calls[0]["episode_body"] == "ported edge"
    assert fake.add_calls[0]["group_id"] == _group_id(SCOPE)
    assert report.transferred == 1


def test_group_id_is_injective_across_distinct_scopes():
    # Two DISTINCT scopes must NEVER yield the same graphiti group_id. The
    # discriminating case is the agent/session positional swap: a naive "skip
    # None and join" collapses both to "acme:x". The encoding must keep them apart.
    scopes = [
        Scope(tenant="acme"),
        Scope(tenant="acme", agent="x"),
        Scope(tenant="acme", session="x"),  # swap-of-the-above — the trap
        Scope(tenant="acme", agent="x", session="y"),
        Scope(tenant="acme2", agent="x"),
        Scope(tenant="acme", agent="x", session="x"),
    ]
    gids = [_group_id(s) for s in scopes]
    assert len(set(gids)) == len(gids), f"collision among group_ids: {gids}"
    # the specific cross-scope collision the bug report calls out:
    assert _group_id(Scope(tenant="acme", agent="x")) != _group_id(
        Scope(tenant="acme", session="x")
    )


async def test_no_graphiti_type_leaks_across_boundary():
    fake = FakeGraphiti()
    # Embed the native sentinel edge so it is reachable via the engine return; the
    # adapter must surface NONE of it across the boundary.
    sentinel = FakeEdge("clean fact", "u1", group_id=_group_id(SCOPE))
    fake._edges = [sentinel]
    be = GraphitiBackend(client=fake)
    out = await be.recall("q", SCOPE)

    assert out and all(isinstance(r, Recollection) for r in out)
    # The sentinel edge object must appear NOWHERE in the returned data — not as the
    # Recollection, not in any scalar field, and not in ANY metadata value.
    for r in out:
        assert not isinstance(r, FakeEdge)
        assert isinstance(r.text, str)
        assert not isinstance(r.text, FakeEdge)
        assert isinstance(r.source_id, str)
        assert not isinstance(r.source_id, FakeEdge)
        assert not isinstance(r.when, FakeEdge)
        assert r.when is not sentinel
        for v in r.metadata.values():
            assert not isinstance(v, FakeEdge)
            assert v is not sentinel


async def test_openai_compatible_config_builds_official_generic_clients():
    pytest.importorskip("graphiti_core")
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    from graphiti_core.embedder.openai import OpenAIEmbedder
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

    llm_client, embedder, cross_encoder = _openai_compatible_clients(
        llm_provider="openai_generic",
        llm_api_key="llm-key",
        llm_model="portable-chat",
        llm_base_url="https://llm.example/v1",
        embedder_api_key="embed-key",
        embedder_model="portable-embed",
        embedder_base_url="https://embed.example/v1",
        embedding_dim=4096,
    )
    try:
        assert isinstance(llm_client, OpenAIGenericClient)
        assert getattr(llm_client, _NORMALIZED_FLAG) is True
        assert llm_client.model == "portable-chat"
        assert str(llm_client.client.base_url) == "https://llm.example/v1/"
        assert isinstance(embedder, OpenAIEmbedder)
        assert embedder.config.embedding_model == "portable-embed"
        assert embedder.config.embedding_dim == 4096
        assert str(embedder.client.base_url) == "https://embed.example/v1/"
        assert isinstance(cross_encoder, OpenAIRerankerClient)
        assert cross_encoder.client is llm_client.client
    finally:
        await llm_client.client.close()
        await embedder.client.close()
