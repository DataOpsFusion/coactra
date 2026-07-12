"""Directory-backed authorization for memory reads and writes."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from coactra.scope import Scope


class ScopeViolation(PermissionError):
    """Raised when an agent attempts an unauthorized memory write."""


def read_action(scope: Scope) -> str:
    """Return the directory permission token for a scoped memory read."""
    return scope_read_action(scope)


def write_action(scope: Scope) -> str:
    """Return the directory permission token for a scoped memory write."""
    return scope_write_action(scope)


def _scope_action(scope: Scope, action: str) -> str:
    """Return the directory permission token for an exact canonical memory scope."""
    return f"memory:{action}:{scope.key}"


def scope_read_action(scope: Scope) -> str:
    """Return the directory permission token for an exact memory scope read."""
    return _scope_action(scope, "read")


def scope_write_action(scope: Scope) -> str:
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

    def check_read(self, agent_name: str, scope: Scope) -> None:
        """Permit a scoped read or fail closed with ScopeViolation."""
        self._check(agent_name, scope_read_action(scope), "read")

    def check_write(self, agent_name: str, scope: Scope) -> None:
        """Permit a scoped write or fail closed with ScopeViolation."""
        self._check(agent_name, scope_write_action(scope), "write")

    @classmethod
    def for_scopes(
        cls,
        *,
        tenant: str,
        agent_name: str,
        writable_scopes: Iterable[Scope],
        readable_scopes: Iterable[Scope] = (),
        org_name: str = "homelab",
    ) -> MemoryAcl:
        """Seed a minimal directory granting an agent an explicit scope allowlist."""
        from coactra.team.directory import Organization

        scopes = list(writable_scopes)
        readable = list(readable_scopes)
        if any(scope.tenant_id != tenant for scope in scopes + readable):
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
        from coactra.scope import Scope

        return cls.for_scopes(
            tenant=tenant,
            agent_name=agent_name,
            writable_scopes=[Scope(tenant_id=tenant, agent_id=agent_name)],
            readable_scopes=[Scope(tenant_id=tenant, agent_id=agent_name)],
            org_name=org_name,
        )
