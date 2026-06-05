import coactra.memory as m


def test_public_surface_is_exact():
    expected = {
        "__version__",
        "Memory",
        "make_backend",
        "Scope",
        "Recollection",
        "MemoryEvent",
        "MemoryBackend",
        "MemoryAccess",
        "MemoryAccessDenied",
        "MemoryAuthorizer",
        "AllowListMemoryAuthorizer",
        "AuthorizedMemory",
        "Capability",
        "MemoryBackendReport",
        "check_memory_backend_contract",
        "ExportReport",
        "export",
        "TenantMemoryBackendRouter",
    }
    assert set(m.__all__) == expected
    for name in expected:
        assert hasattr(m, name), name


async def test_end_to_end_remember_recall_export_via_facade():
    mem = m.Memory(backend=m.make_backend("inprocess"))
    dst = m.make_backend("inprocess")
    scope = m.Scope(tenant="acme", agent="agent1")

    await mem.remember(["the build broke on the linter step"], scope)
    hits = await mem.recall("why did the build break", scope)
    assert hits and "build broke" in hits[0].text
    assert isinstance(hits[0], m.Recollection)

    report = await mem.export(to=dst, scope=scope)
    assert report.transferred == 1
    assert report.lossless is True
