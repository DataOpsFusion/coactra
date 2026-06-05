"""Shared scope mapping helpers for Coactra packages.

The individual packages intentionally keep their own small Scope classes so they
can be installed independently. This module provides a canonical DTO and explicit
conversion kwargs for applications that compose multiple Coactra packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_RESERVED = {":", "*", "\x00"}
_PATH_RESERVED = {"/", "\\"}


def _validate_component(name: str, value: str, *, path_safe: bool = False) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    invalid = _RESERVED | (_PATH_RESERVED if path_safe else set())
    if any(ch in value for ch in invalid):
        chars = "".join(sorted(invalid))
        raise ValueError(f"{name} must not contain reserved characters: {chars!r}")


@dataclass(frozen=True, slots=True)
class CoactraScope:
    """Canonical scope DTO for apps that compose Coactra packages.

    Field mapping:
    - tenant_id: security and ownership boundary shared by all packages.
    - namespace: logical partition for agent, orchestration, workflow, and memory.
    - agent_id: required for workspace scopes, optional narrowing dimension for memory.
    - session_id: optional narrowing dimension for memory/session-specific state.
    """

    tenant_id: str
    namespace: str = "default"
    agent_id: str | None = None
    session_id: str | None = None

    def __post_init__(self) -> None:
        _validate_component("tenant_id", self.tenant_id)
        _validate_component("namespace", self.namespace)
        if self.agent_id is not None:
            _validate_component("agent_id", self.agent_id)
        if self.session_id is not None:
            _validate_component("session_id", self.session_id)

    @property
    def key(self) -> str:
        """Stable canonical key suitable for logs, metrics, and tests."""
        agent = self.agent_id or "*"
        session = self.session_id or "*"
        return f"{self.tenant_id}:{self.namespace}:{agent}:{session}"

    def to_agent_kwargs(self) -> dict[str, str]:
        """Keyword arguments for ``coactra.agent.Scope``."""
        return {"tenant_id": self.tenant_id, "namespace": self.namespace}

    def to_work_kwargs(self) -> dict[str, str]:
        """Keyword arguments for ``coactra.jobs.Scope``."""
        return {"tenant_id": self.tenant_id, "namespace": self.namespace}

    def to_workflow_kwargs(self) -> dict[str, str]:
        """Keyword arguments for ``coactra.jobs.workflow.Scope``."""
        return {"tenant_id": self.tenant_id, "namespace": self.namespace}

    def to_memory_kwargs(self) -> dict[str, str | None]:
        """Keyword arguments for ``coactra.memory.Scope``."""
        return {
            "tenant": self.tenant_id,
            "namespace": self.namespace,
            "agent": self.agent_id,
            "session": self.session_id,
        }

    def to_workspace_kwargs(self) -> dict[str, str]:
        """Keyword arguments for ``coactra.workspace.Scope``.

        Workspace scopes require an agent id because workspaces are allocated per
        tenant/agent pair and must be path-safe.
        """
        if self.agent_id is None:
            raise ValueError("agent_id is required to create a workspace scope")
        _validate_component("agent_id", self.agent_id, path_safe=True)
        _validate_component("tenant_id", self.tenant_id, path_safe=True)
        return {"tenant_id": self.tenant_id, "agent_id": self.agent_id}

    def as_event_metadata(self) -> dict[str, Any]:
        """Serializable scope metadata for work events and audit logs."""
        return {
            "tenant_id": self.tenant_id,
            "namespace": self.namespace,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "scope_key": self.key,
        }


__all__ = ["CoactraScope"]
