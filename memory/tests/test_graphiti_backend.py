"""GraphitiBackend unit tests with a MOCKED graphiti client.

Proves: (1) native-async engine calls + group_id mapping (singular on add_episode,
plural group_ids on search), (2) EntityEdge → Recollection mapping, (3) NO graphiti
type leaks across the boundary (sentinel-edge proof).
"""

from datetime import datetime, timezone

from fleetlib.memory import Recollection, Scope
from fleetlib.memory.backends.graphiti import GraphitiBackend, _group_id


class FakeEdge:
    """Stand-in for graphiti_core EntityEdge — must NEVER cross the boundary."""

    def __init__(self, fact, uuid, valid_at=None, group_id=None):
        self.fact = fact
        self.uuid = uuid
        self.valid_at = valid_at
        self.group_id = group_id


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
