"""Mem0Backend unit tests with a MOCKED mem0 client.

Proves: (1) correct engine method + scope mapping, (2) result → Recollection mapping,
(3) NO mem0 type leaks across the boundary (sentinel-object proof).
"""

from coactra.memory import Recollection, Scope
from coactra.memory.backends.mem0 import Mem0Backend


class _Mem0Sentinel:
    """A fake mem0 native object that must NEVER cross the adapter boundary."""

    def __init__(self, memory: str):
        self.memory = memory


class FakeMem0:
    """Stand-in for mem0.Memory. Records calls; returns mem0-shaped result dicts."""

    def __init__(self):
        self.add_calls = []
        self.search_calls = []
        self.get_all_calls = []
        self._search_payload = {"results": []}

    def add(self, messages, **kwargs):
        self.add_calls.append((messages, kwargs))
        return {"results": [{"id": "m1", "memory": "added", "event": "ADD"}]}

    def search(self, query, filters=None, top_k=None):
        self.search_calls.append({"query": query, "filters": filters, "top_k": top_k})
        return self._search_payload

    def get_all(self, *, filters=None):
        self.get_all_calls.append({"filters": filters})
        return {"results": [{"id": "g1", "memory": "stored fact", "metadata": {}}]}


SCOPE = Scope(tenant="acme", agent="builder", session="sess1")


async def test_remember_calls_add_with_scope_mapping():
    fake = FakeMem0()
    be = Mem0Backend(client=fake)
    await be.remember(["user likes dark mode"], SCOPE)

    assert len(fake.add_calls) == 1
    messages, kwargs = fake.add_calls[0]
    assert messages == [{"role": "user", "content": "user likes dark mode"}]
    # tenant ALWAYS maps to user_id (isolation); agent/session map to agent_id/run_id.
    assert kwargs == {"user_id": "acme", "agent_id": "builder", "run_id": "sess1"}


async def test_namespaced_scope_uses_reserved_injective_agent_id():
    fake = FakeMem0()
    be = Mem0Backend(client=fake)
    scope = Scope(tenant="acme", namespace="department/infrastructure")
    await be.remember(["shared fact"], scope)

    _, kwargs = fake.add_calls[0]
    assert kwargs == {
        "user_id": "acme",
        "agent_id": "namespace:" + scope.key.encode("utf-8").hex(),
    }
    assert kwargs["agent_id"] != "department/infrastructure"


async def test_remember_passes_chat_dicts_through():
    fake = FakeMem0()
    be = Mem0Backend(client=fake)
    msg = {"role": "assistant", "content": "noted"}
    await be.remember([msg], SCOPE)
    messages, _ = fake.add_calls[0]
    assert messages == [msg]


async def test_recall_calls_search_with_filters_and_top_k():
    fake = FakeMem0()
    fake._search_payload = {
        "results": [
            {
                "id": "abc",
                "memory": "the deploy used blue-green",
                "score": 0.87,
                "created_at": "2026-01-02T03:04:05Z",
                "metadata": {"topic": "deploy"},
            }
        ]
    }
    be = Mem0Backend(client=fake)
    out = await be.recall("deploy strategy", SCOPE, k=7)

    call = fake.search_calls[0]
    assert call["query"] == "deploy strategy"
    assert call["filters"] == {
        "user_id": "acme",
        "agent_id": "builder",
        "run_id": "sess1",
    }
    assert call["top_k"] == 7

    assert len(out) == 1
    rec = out[0]
    assert isinstance(rec, Recollection)
    assert rec.text == "the deploy used blue-green"
    assert rec.score == 0.87
    assert rec.source_id == "abc"
    assert rec.when is not None and rec.when.year == 2026
    assert rec.metadata["source_backend"] == "mem0"
    assert rec.metadata["topic"] == "deploy"


async def test_recall_tolerates_bare_list_payload():
    fake = FakeMem0()
    fake._search_payload = [{"id": "x", "memory": "legacy shape"}]  # older mem0 builds
    be = Mem0Backend(client=fake)
    out = await be.recall("q", SCOPE)
    assert [r.text for r in out] == ["legacy shape"]


async def test_dump_calls_get_all_with_scope_and_maps_results():
    fake = FakeMem0()
    be = Mem0Backend(client=fake)
    out = await be.dump(SCOPE)

    assert fake.get_all_calls[0] == {
        "filters": {
            "user_id": "acme",  # tenant always present in the scope key (isolation)
            "agent_id": "builder",
            "run_id": "sess1",
        },
    }
    assert [r.text for r in out] == ["stored fact"]
    assert all(isinstance(r, Recollection) for r in out)
    assert out[0].metadata["source_backend"] == "mem0"


async def test_ingest_writes_via_add_and_reports_transferred():
    fake = FakeMem0()
    be = Mem0Backend(client=fake)
    report = await be.ingest(
        [Recollection(text="ported fact"), Recollection(text="")], SCOPE
    )
    # empty-text recollection is skipped; one message written.
    messages, kwargs = fake.add_calls[0]
    assert messages == [{"role": "user", "content": "ported fact"}]
    assert kwargs["user_id"] == "acme"
    assert report.transferred == 1


async def test_no_mem0_type_leaks_across_boundary():
    fake = FakeMem0()
    # Embed a native sentinel object inside the result; the adapter must not propagate it.
    fake._search_payload = {
        "results": [
            {"id": "1", "memory": "clean text", "engine_obj": _Mem0Sentinel("raw")}
        ]
    }
    be = Mem0Backend(client=fake)
    out = await be.recall("q", SCOPE)

    assert out and all(isinstance(r, Recollection) for r in out)
    # The sentinel engine object must appear NOWHERE in the returned data.
    for r in out:
        assert not isinstance(r, _Mem0Sentinel)
        assert not isinstance(r.text, _Mem0Sentinel)
        for v in r.metadata.values():
            assert not isinstance(v, _Mem0Sentinel)
