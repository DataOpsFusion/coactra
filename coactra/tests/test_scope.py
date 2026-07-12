from __future__ import annotations

import pytest

from coactra.scope import Scope


def test_scope_has_stable_canonical_key() -> None:
    scope = Scope(
        tenant_id="tenant-a",
        namespace="support",
        agent_id="triage",
        session_id="session-1",
    )

    assert scope.key == "tenant-a:support:triage:session-1"
    assert scope.as_event_metadata() == {
        "tenant_id": "tenant-a",
        "namespace": "support",
        "agent_id": "triage",
        "session_id": "session-1",
        "scope_key": "tenant-a:support:triage:session-1",
    }


def test_scope_rejects_reserved_key_characters() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        Scope(tenant_id="tenant:a")
    with pytest.raises(ValueError, match="namespace"):
        Scope(tenant_id="tenant-a", namespace="*")


def test_scope_allows_memory_namespace_paths() -> None:
    assert Scope(tenant_id="tenant-a", namespace="department/infrastructure").namespace == (
        "department/infrastructure"
    )
