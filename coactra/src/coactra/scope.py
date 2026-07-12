"""The single canonical scope shared by every Coactra package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_RESERVED = {":", "*", "\x00"}
# Components that must be a single, non-escaping path segment (workspace desks).
_PATH_INVALID = {"/", "\\", "\x00"}
_PATH_RESERVED_NAMES = {".", ".."}


def _validate_component(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if any(ch in value for ch in _RESERVED):
        chars = "".join(sorted(_RESERVED))
        raise ValueError(f"{name} must not contain reserved characters: {chars!r}")


def is_safe_path_component(value: str) -> bool:
    """Return True if ``value`` is a single, non-escaping path segment.

    Shared rule backing per-tenant/namespace/agent workspace desks: a value must not be
    ``.``/``..`` and must not contain a path separator or NUL byte, so it can never
    escape its desk root. This is the canonical home for the rule; workspace
    boundaries call this helper before constructing a filesystem path.
    """
    if value in _PATH_RESERVED_NAMES:
        return False
    return not any(ch in value for ch in _PATH_INVALID)


@dataclass(frozen=True, slots=True)
class Scope:
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

    def as_event_metadata(self) -> dict[str, Any]:
        """Serializable scope metadata for work events and audit logs."""
        return {
            "tenant_id": self.tenant_id,
            "namespace": self.namespace,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "scope_key": self.key,
        }


__all__ = [
    "Scope",
    "is_safe_path_component",
]
