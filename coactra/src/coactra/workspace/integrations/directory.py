"""Directory-backed authorization for memory reads and writes."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class ScopeViolation(PermissionError):
    """Raised when an agent attempts an unauthorized memory write."""


def read_action(tenant: str, agent: str) -> str:
    """Return the directory permission token for an agent-owned memory read."""
    return f"memory:read:{tenant}:{agent}"


def write_action(tenant: str, agent: str) -> str:
    """Return the directory permission token for an agent-owned memory write."""
    return f"memory:write:{tenant}:{agent}"


def _scope_action(scope: Any, action: str) -> str:
    """Return the directory permission token for an exact memory scope.

    Agent-owned scopes use the concise per-agent permission token. Shared scopes
    use the full collision-resistant key.
    """
    if scope.namespace is None and scope.agent is not None and scope.session is None:
        return f"memory:{action}:{scope.tenant}:{scope.agent}"
    return f"memory:{action}:{scope.key}"


def scope_read_action(scope: Any) -> str:
    """Return the directory permission token for an exact memory scope read."""
    return _scope_action(scope, "read")


def scope_write_action(scope: Any) -> str:
    """Return the directory permission token for an exact memory scope write."""
    return _scope_action(scope, "write")


class MemoryAcl:
    """Resolve memory read/write permission through a directory facade."""

    def __init__(self, org: Any, *, member_for: dict[str, Any] | None = None) -> None:
        self._org = org
        self._members: dict[str, Any] = dict(member_for or {})

    def register_member(self, agent_name: str, member: Any) -> None:
        self._members[agent_name] = member

    def _check(self, agent_name: str, action: str, operation: str) -> None:
        member = self._members.get(agent_name)
        if member is None:
            raise ScopeViolation(
                f"agent {agent_name!r} has no directory membership; "
                f"refusing memory {operation} to {action!r} (fail-closed)"
            )
        if not self._org.can(member, action):
            raise ScopeViolation(
                f"agent {agent_name!r} is not permitted {action!r} (directory can check denied)"
            )

    def check_read(self, agent_name: str, scope: Any) -> None:
        """Permit a scoped read or fail closed with ScopeViolation."""
        self._check(agent_name, scope_read_action(scope), "read")

    def check_write(self, agent_name: str, scope: Any) -> None:
        """Permit a scoped write or fail closed with ScopeViolation."""
        self._check(agent_name, scope_write_action(scope), "write")

    @classmethod
    def for_scopes(
        cls,
        *,
        tenant: str,
        agent_name: str,
        writable_scopes: Iterable[Any],
        readable_scopes: Iterable[Any] = (),
        org_name: str = "homelab",
    ) -> MemoryAcl:
        """Seed a minimal directory granting an agent an explicit scope allowlist."""
        from coactra.team.directory import Organization

        scopes = list(writable_scopes)
        readable = list(readable_scopes)
        if any(scope.tenant != tenant for scope in scopes + readable):
            raise ValueError("every memory scope must belong to the ACL tenant")
        org = Organization.root(tenant=tenant, name=org_name)
        permissions = {scope_write_action(scope) for scope in scopes}
        permissions.update(scope_read_action(scope) for scope in readable)
        member = org.hire(agent_name, kind="agent", permissions=permissions)
        return cls(org, member_for={agent_name: member})

    @classmethod
    def for_own_scope(
        cls,
        *,
        tenant: str,
        agent_name: str,
        org_name: str = "homelab",
    ) -> MemoryAcl:
        """Seed a minimal directory granting only the agent-owned memory scope."""
        from coactra.memory import Scope

        return cls.for_scopes(
            tenant=tenant,
            agent_name=agent_name,
            writable_scopes=[Scope(tenant=tenant, agent=agent_name)],
            readable_scopes=[Scope(tenant=tenant, agent=agent_name)],
            org_name=org_name,
        )
