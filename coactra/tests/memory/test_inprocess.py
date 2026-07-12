from coactra.memory import Capability, Recollection, Scope
from coactra.memory.backends.inprocess import InProcessBackend

SCOPE = Scope(tenant_id="acme", agent_id="agent1")


async def test_remember_stores_recollections_with_lineage():
    be = InProcessBackend()
    await be.remember(["dark mode preferred", {"role": "user", "content": "deploy ok"}], SCOPE)
    dumped = await be.dump(SCOPE)
    assert {r.text for r in dumped} == {"dark mode preferred", "deploy ok"}
    assert all(r.metadata["source_backend"] == "inprocess" for r in dumped)
    assert all(isinstance(r, Recollection) for r in dumped)


async def test_remember_dedups_identical_text_in_scope():
    be = InProcessBackend()
    await be.remember(["same lesson"], SCOPE)
    await be.remember(["same lesson"], SCOPE)
    assert len(await be.dump(SCOPE)) == 1


async def test_remember_skips_empty_events():
    be = InProcessBackend()
    await be.remember(["", {"role": "user", "content": "  "}], SCOPE)
    assert await be.dump(SCOPE) == []


async def test_capabilities_are_store_lexical_provenance():
    assert await InProcessBackend().capabilities() == {
        Capability.STORE,
        Capability.LEXICAL_RECALL,
        Capability.PROVENANCE,
    }


async def _seeded():
    be = InProcessBackend()
    await be.remember(
        [
            "deployment failed because the port was busy",
            "user prefers dark mode in the editor",
            "backup completed in 12 seconds",
        ],
        SCOPE,
    )
    return be


async def test_recall_ranks_token_overlap_first_with_score():
    be = await _seeded()
    out = await be.recall("why did the deployment fail", SCOPE)
    assert out
    assert "deployment failed" in out[0].text
    assert out[0].score > 0


async def test_recall_respects_k():
    be = await _seeded()
    out = await be.recall("the", SCOPE, k=1)
    assert len(out) <= 1


async def test_recall_returns_empty_on_no_match():
    be = await _seeded()
    assert await be.recall("xylophone unicorn", SCOPE) == []
