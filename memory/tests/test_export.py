import pytest

from fleetlib.memory import (
    Capability,
    ExportReport,
    InProcessBackend,
    MemoryBackend,
    Scope,
    export,
)

SCOPE = Scope(tenant_id="acme", namespace="agent:1")


class _GraphBackend:
    """A fake source that claims graph + temporal capabilities the target lacks."""

    def __init__(self):
        self._inner = InProcessBackend()

    def capabilities(self):
        return {
            Capability.STORE,
            Capability.GRAPH_EDGES,
            Capability.TEMPORAL,
            Capability.PROVENANCE,
        }

    def learn(self, events, scope):
        return self._inner.learn(events, scope)

    def recall(self, query, scope, capabilities=None, limit=10):
        return self._inner.recall(query, scope, capabilities, limit)

    def dump(self, scope):
        return self._inner.dump(scope)

    def ingest(self, items, scope):
        return self._inner.ingest(items, scope)


def test_export_returns_report_and_moves_items():
    src = _GraphBackend()
    dst = InProcessBackend()
    src.learn(["a relationship between A and B", "an event at noon"], SCOPE)

    report = export(src, dst, scope=SCOPE)

    assert isinstance(report, ExportReport)
    assert report.transferred == 2
    assert {i.content for i in dst.dump(SCOPE)} == {
        "a relationship between A and B",
        "an event at noon",
    }


def test_export_reports_dropped_features_and_is_never_lossless():
    src = _GraphBackend()              # GRAPH_EDGES + TEMPORAL
    dst = InProcessBackend()           # neither
    src.learn(["x"], SCOPE)

    report = export(src, dst, scope=SCOPE)

    assert Capability.GRAPH_EDGES in report.dropped_capabilities
    assert Capability.TEMPORAL in report.dropped_capabilities
    assert report.lossless is False
    assert any("GRAPH_EDGES" in w for w in report.warnings)


def test_export_preserves_provenance_lineage():
    src = _GraphBackend()
    dst = InProcessBackend()
    src.learn(["traceable"], SCOPE)

    export(src, dst, scope=SCOPE)
    moved = dst.dump(SCOPE)[0]
    assert moved.provenance.exported_from is not None
    # export must COPY, not alias: the source's own item is untouched.
    assert src.dump(SCOPE)[0].provenance.exported_from is None


def test_same_capability_export_is_lossless():
    src = InProcessBackend()
    dst = InProcessBackend()
    src.learn(["plain note"], SCOPE)

    report = export(src, dst, scope=SCOPE)
    assert report.dropped_capabilities == set()
    assert report.lossless is True


def test_export_is_scope_isolated():
    src = InProcessBackend()
    dst = InProcessBackend()
    other = Scope(tenant_id="acme", namespace="agent:2")
    src.learn(["only in agent:1"], SCOPE)
    src.learn(["only in agent:2"], other)

    export(src, dst, scope=SCOPE)
    assert {i.content for i in dst.dump(SCOPE)} == {"only in agent:1"}
    assert dst.dump(other) == []


def test_backends_satisfy_protocol():
    assert isinstance(_GraphBackend(), MemoryBackend)
    assert isinstance(InProcessBackend(), MemoryBackend)
