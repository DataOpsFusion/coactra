from coactra.memory import Capability, ExportReport, MemoryExporter, Scope, export
from coactra.memory.backends.inprocess import InProcessBackend

SCOPE = Scope(tenant_id="acme", agent_id="agent1")


class _GraphBackend:
    """A fake source claiming graph + temporal capabilities the target lacks."""

    def __init__(self):
        self._inner = InProcessBackend()

    async def capabilities(self):
        return {
            Capability.STORE,
            Capability.GRAPH_EDGES,
            Capability.TEMPORAL,
            Capability.PROVENANCE,
        }

    async def remember(self, events, scope):
        await self._inner.remember(events, scope)

    async def recall(self, query, scope, k=10):
        return await self._inner.recall(query, scope, k)

    async def dump(self, scope):
        return await self._inner.dump(scope)

    async def ingest(self, items, scope):
        return await self._inner.ingest(items, scope)


async def test_export_moves_items_and_reports():
    src = _GraphBackend()
    dst = InProcessBackend()
    await src.remember(["a relationship between A and B", "an event at noon"], SCOPE)

    report = await export(src, dst, scope=SCOPE)
    assert isinstance(report, ExportReport)
    assert report.transferred == 2
    assert {r.text for r in await dst.dump(SCOPE)} == {
        "a relationship between A and B",
        "an event at noon",
    }


async def test_export_reports_dropped_features_and_is_never_lossless():
    src = _GraphBackend()  # GRAPH_EDGES + TEMPORAL
    dst = InProcessBackend()  # neither
    await src.remember(["x"], SCOPE)

    report = await export(src, dst, scope=SCOPE)
    assert Capability.GRAPH_EDGES in report.dropped_capabilities
    assert Capability.TEMPORAL in report.dropped_capabilities
    assert report.lossless is False
    assert any("GRAPH_EDGES" in w for w in report.warnings)


async def test_export_preserves_lineage_and_does_not_mutate_source():
    src = _GraphBackend()
    dst = InProcessBackend()
    await src.remember(["traceable"], SCOPE)

    await export(src, dst, scope=SCOPE)
    moved = (await dst.dump(SCOPE))[0]
    assert moved.metadata.get("exported_from") is not None
    # COPY, not alias: the source item is untouched.
    assert "exported_from" not in (await src.dump(SCOPE))[0].metadata


async def test_same_capability_export_is_lossless():
    src = InProcessBackend()
    dst = InProcessBackend()
    await src.remember(["plain note"], SCOPE)

    report = await export(src, dst, scope=SCOPE)
    assert report.dropped_capabilities == set()
    assert report.lossless is True


async def test_export_is_scope_isolated():
    src = InProcessBackend()
    dst = InProcessBackend()
    other = Scope(tenant_id="acme", agent_id="agent2")
    await src.remember(["only in agent1"], SCOPE)
    await src.remember(["only in agent2"], other)

    await export(src, dst, scope=SCOPE)
    assert {r.text for r in await dst.dump(SCOPE)} == {"only in agent1"}
    assert await dst.dump(other) == []


def test_backends_satisfy_protocol():
    assert isinstance(_GraphBackend(), MemoryExporter)
    assert isinstance(InProcessBackend(), MemoryExporter)
