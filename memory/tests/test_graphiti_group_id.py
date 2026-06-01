"""Regression: the graphiti group_id must be graphiti-LEGAL and INJECTIVE.

Found by live testing (2026-06): the memory-v2 collision fix used a ``tenant:agent:*``
key, but graphiti's ``validate_group_id`` rejects ':' and '*' (only ``[A-Za-z0-9_-]``).
The hex-encoding fix must stay legal AND collision-resistant across distinct scopes.
"""

import re

import pytest

from fleetlib.memory import Scope
from fleetlib.memory.backends.graphiti import _group_id

_LEGAL = re.compile(r"[A-Za-z0-9_-]+")


def test_group_id_is_graphiti_legal():
    scopes = [
        Scope(tenant="acme"),
        Scope(tenant="acme", agent="builder"),
        Scope(tenant="acme", agent="builder", session="s1"),
        Scope(tenant="a_b-c", agent="x-y_z"),
    ]
    for s in scopes:
        gid = _group_id(s)
        assert _LEGAL.fullmatch(gid), f"illegal graphiti group_id: {gid!r} for {s}"


def test_group_id_is_injective_across_distinct_scopes():
    scopes = [
        Scope(tenant="acme", agent="x"),
        Scope(tenant="acme", session="x"),  # must NOT alias the agent="x" scope
        Scope(tenant="acme"),
        Scope(tenant="acmex"),
        Scope(tenant="acme", agent="x", session="y"),
    ]
    seen: dict[str, Scope] = {}
    for s in scopes:
        gid = _group_id(s)
        assert gid not in seen, f"collision {gid!r}: {s} vs {seen[gid]}"
        seen[gid] = s


def test_group_id_passes_graphitis_own_validator_if_installed():
    try:
        from graphiti_core.helpers import validate_group_id
    except Exception:
        pytest.skip("graphiti-core not installed")
    # must not raise GroupIdValidationError
    validate_group_id(_group_id(Scope(tenant="acme", agent="builder", session="run1")))
