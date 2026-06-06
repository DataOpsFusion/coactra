"""Tests for coactra.agent.sdk.memory — bind_memory / MemoryBinding.

TDD: written RED (before the module exists), then GREEN once memory.py is implemented.
"""

from __future__ import annotations

from coactra.memory import make_backend, Scope

from coactra.agent.sdk.memory import bind_memory, MemoryBinding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scope(agent: str = "a") -> Scope:
    return Scope(tenant="test", agent=agent)


# ---------------------------------------------------------------------------
# 1. Basic remember → recall roundtrip
# ---------------------------------------------------------------------------

async def test_remember_and_recall_basic():
    """A stored fact can be recalled via a relevant query."""
    scope = _scope("basic")
    backend = make_backend("inprocess")
    b = bind_memory(backend, scope)

    await b.remember("prod DB is on 192.168.0.66")
    result = await b.recall("where is prod db")

    assert isinstance(result, str)
    assert result != ""
    # The fact text should appear in the formatted context string
    assert "prod" in result.lower() or "66" in result.lower()


# ---------------------------------------------------------------------------
# 2. max_recall cap
# ---------------------------------------------------------------------------

async def test_max_recall_cap():
    """recall returns at most max_recall items in the context string."""
    max_recall = 3
    scope = _scope("cap")
    backend = make_backend("inprocess")
    b = bind_memory(backend, scope, max_recall=max_recall)

    # Store more facts than the cap; all share the token "deploy" so they all score.
    for i in range(10):
        await b.remember(f"deploy note {i} — server restarted successfully")

    result = await b.recall("deploy server")

    # Each recollection is on its own line; the number of non-empty lines ≤ max_recall.
    lines = [line for line in result.splitlines() if line.strip()]
    assert len(lines) <= max_recall
    assert len(lines) > 0  # at least one hit


# ---------------------------------------------------------------------------
# 3. Scope isolation
# ---------------------------------------------------------------------------

async def test_scope_isolation():
    """A fact stored under scope A is not visible under scope B."""
    scope_a = _scope("agent-a")
    scope_b = _scope("agent-b")
    backend = make_backend("inprocess")  # shared backend instance, different scopes

    b_a = bind_memory(backend, scope_a)
    b_b = bind_memory(backend, scope_b)

    await b_a.remember("secret fact about scope A deployment")
    result = await b_b.recall("secret fact scope deployment")

    # Scope B should find nothing from scope A
    assert result == ""


# ---------------------------------------------------------------------------
# 4. write_policy veto — remember stores nothing when policy returns False
# ---------------------------------------------------------------------------

async def test_write_policy_veto():
    """A write_policy that always returns False prevents remember from storing."""
    scope = _scope("veto")
    backend = make_backend("inprocess")
    b = bind_memory(backend, scope, write_policy=lambda text: False)

    await b.remember("this should never be stored")
    result = await b.recall("this should never stored")

    assert result == ""


# ---------------------------------------------------------------------------
# 5. write_policy allow — policy returning True stores normally
# ---------------------------------------------------------------------------

async def test_write_policy_allow():
    """A write_policy returning True allows the remember to proceed normally."""
    scope = _scope("allow")
    backend = make_backend("inprocess")
    b = bind_memory(backend, scope, write_policy=lambda text: True)

    await b.remember("allowed fact stored fine")
    result = await b.recall("allowed fact stored")

    assert result != ""


# ---------------------------------------------------------------------------
# 6. bind_memory accepts a name string (auto-constructs the backend)
# ---------------------------------------------------------------------------

async def test_bind_memory_from_name():
    """bind_memory('inprocess', scope) constructs a backend and works correctly."""
    scope = _scope("namestr")
    b = bind_memory("inprocess", scope)

    assert isinstance(b, MemoryBinding)
    await b.remember("name-string backend works")
    result = await b.recall("name string backend")
    assert result != ""


# ---------------------------------------------------------------------------
# 7. recall returns "" when nothing is stored
# ---------------------------------------------------------------------------

async def test_recall_empty():
    """recall returns an empty string when the backend has no matching memories."""
    scope = _scope("empty")
    b = bind_memory("inprocess", scope)

    result = await b.recall("anything at all")
    assert result == ""


# ---------------------------------------------------------------------------
# 8. source kwarg is accepted (best-effort provenance, no crash)
# ---------------------------------------------------------------------------

async def test_remember_source_accepted():
    """source= kwarg is accepted without error; fact is still recalled."""
    scope = _scope("source")
    b = bind_memory("inprocess", scope)

    await b.remember("sourced fact about the database", source="turn-42")
    result = await b.recall("sourced fact database")

    assert result != ""
