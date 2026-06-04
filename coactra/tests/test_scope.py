from __future__ import annotations

import pytest

from coactra.scope import CoactraScope


def test_scope_has_stable_canonical_key() -> None:
    scope = CoactraScope(
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


def test_scope_conversion_kwargs_match_package_field_names() -> None:
    scope = CoactraScope(
        tenant_id="tenant-a",
        namespace="support",
        agent_id="triage",
        session_id="session-1",
    )

    assert scope.to_agent_kwargs() == {"tenant_id": "tenant-a", "namespace": "support"}
    assert scope.to_work_kwargs() == {"tenant_id": "tenant-a", "namespace": "support"}
    assert scope.to_workflow_kwargs() == {"tenant_id": "tenant-a", "namespace": "support"}
    assert scope.to_workspace_kwargs() == {"tenant_id": "tenant-a", "agent_id": "triage"}
    assert scope.to_memory_kwargs() == {
        "tenant": "tenant-a",
        "namespace": "support",
        "agent": "triage",
        "session": "session-1",
    }


def test_scope_rejects_reserved_memory_separator_characters() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        CoactraScope(tenant_id="tenant:a")
    with pytest.raises(ValueError, match="namespace"):
        CoactraScope(tenant_id="tenant-a", namespace="*")


def test_workspace_conversion_requires_agent_and_path_safe_values() -> None:
    with pytest.raises(ValueError, match="agent_id is required"):
        CoactraScope(tenant_id="tenant-a").to_workspace_kwargs()

    with pytest.raises(ValueError, match="agent_id"):
        CoactraScope(tenant_id="tenant-a", agent_id="team/agent").to_workspace_kwargs()
