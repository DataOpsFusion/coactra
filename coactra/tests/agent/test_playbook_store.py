"""TDD tests for PlaybookStore — candidate/promoted lifecycle.

RED phase: tests written before playbook_store.py exists.

Covers:
1. save_candidate → get(name) returns playbook
2. save_candidate → find(goal) returns None (candidates not visible via find)
3. promote(name) → find(<goal>) returns the playbook
4. Protocol: InMemoryPlaybookStore satisfies PlaybookStore
5. Multiple playbooks coexist independently
"""

from __future__ import annotations

from coactra.workflow.playbook import Playbook, Step

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_playbook(name: str, goal: str | None = None) -> Playbook:
    """Build a minimal Playbook. goal is ignored here; name IS the identifier."""
    return Playbook(
        name=name,
        steps=[Step(instruction=f"Do {name}", needs="some.skill")],
    )


# ---------------------------------------------------------------------------
# 1. save_candidate + get
# ---------------------------------------------------------------------------


def test_save_candidate_get_returns_playbook():
    """get(name) returns the playbook regardless of candidate/promoted status."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb = _make_playbook("rotate-cert")
    store.save_candidate(pb)

    result = store.get("rotate-cert")
    assert result is pb


def test_get_missing_returns_none():
    """get() returns None for unknown names."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    assert store.get("does-not-exist") is None


# ---------------------------------------------------------------------------
# 2. Candidate is NOT visible via find
# ---------------------------------------------------------------------------


def test_find_candidate_returns_none():
    """find() does not return candidate (unreviewed) playbooks."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb = _make_playbook("rotate-cert")
    store.save_candidate(pb)

    result = store.find("rotate-cert")
    assert result is None


def test_find_returns_none_when_empty():
    """find() on an empty store returns None."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    assert store.find("rotate-cert") is None


# ---------------------------------------------------------------------------
# 3. promote → find returns the playbook
# ---------------------------------------------------------------------------


def test_promote_makes_findable():
    """After promote(name), find(name) returns the playbook."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb = _make_playbook("rotate-cert")
    store.save_candidate(pb)
    store.promote("rotate-cert")

    result = store.find("rotate-cert")
    assert result is pb


def test_find_case_insensitive():
    """find() matches name tokens case-insensitively."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb = _make_playbook("rotate-cert")
    store.save_candidate(pb)
    store.promote("rotate-cert")

    result = store.find("Rotate-Cert")
    assert result is pb


def test_find_keyword_in_goal_string():
    """find() matches when the query contains a token from the name."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb = _make_playbook("rotate-cert")
    store.save_candidate(pb)
    store.promote("rotate-cert")

    # "rotate" is a token in "rotate-cert" → should match
    result = store.find("rotate the cert please")
    assert result is pb


def test_find_no_match_returns_none():
    """find() returns None when no promoted playbook matches the goal."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb = _make_playbook("rotate-cert")
    store.save_candidate(pb)
    store.promote("rotate-cert")

    result = store.find("quantum entanglement")
    assert result is None


# ---------------------------------------------------------------------------
# 4. Protocol structural check
# ---------------------------------------------------------------------------


def test_playbook_store_protocol_satisfied():
    """InMemoryPlaybookStore satisfies the PlaybookStore Protocol (runtime check)."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore, PlaybookStore

    # PlaybookStore should be a runtime_checkable Protocol
    store = InMemoryPlaybookStore()
    assert isinstance(store, PlaybookStore)


def test_protocol_has_required_methods():
    """PlaybookStore Protocol declares all four required methods."""
    from coactra.agent.playbook_store import PlaybookStore

    for method in ("save_candidate", "promote", "get", "find"):
        assert hasattr(PlaybookStore, method), f"PlaybookStore missing method: {method}"


# ---------------------------------------------------------------------------
# 5. Multiple playbooks coexist
# ---------------------------------------------------------------------------


def test_multiple_candidates_coexist():
    """Multiple candidates can be stored independently."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb1 = _make_playbook("rotate-cert")
    pb2 = _make_playbook("deploy-service")
    store.save_candidate(pb1)
    store.save_candidate(pb2)

    assert store.get("rotate-cert") is pb1
    assert store.get("deploy-service") is pb2


def test_promote_one_does_not_affect_other():
    """Promoting one playbook does not promote others."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb1 = _make_playbook("rotate-cert")
    pb2 = _make_playbook("deploy-service")
    store.save_candidate(pb1)
    store.save_candidate(pb2)
    store.promote("rotate-cert")

    # pb2 is still a candidate — not findable
    assert store.find("deploy-service") is None
    # pb1 is promoted — findable
    assert store.find("rotate-cert") is pb1


def test_get_after_promote_still_returns_playbook():
    """get() continues to return the playbook after promotion."""
    from coactra.agent.playbook_store import InMemoryPlaybookStore

    store = InMemoryPlaybookStore()
    pb = _make_playbook("rotate-cert")
    store.save_candidate(pb)
    store.promote("rotate-cert")

    assert store.get("rotate-cert") is pb
