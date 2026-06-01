import fleetlib.memory as m


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "MemoryEvent",
        "MemoryItem",
        "Provenance",
        "Capability",
        "MemoryBackend",
        "InProcessBackend",
        "ExportReport",
        "export",
    }
    assert expected <= set(m.__all__)
    for name in expected:
        assert hasattr(m, name), name


def test_end_to_end_learn_recall_export():
    src = m.InProcessBackend()
    dst = m.InProcessBackend()
    scope = m.Scope(tenant_id="acme", namespace="agent:1")

    src.learn(["the build broke on the linter step"], scope)
    hits = src.recall("why did the build break", scope)
    assert hits and "build broke" in hits[0].content

    report = m.export(src, dst, scope=scope)
    assert report.transferred == 1
    assert report.lossless is True
