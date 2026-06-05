"""In-process FAKES — the ONE working default per port.

Each fake is a faithful, dependency-free stand-in shaped exactly like its port, so the
whole package is unit-testable with zero siblings installed. They are NOT toys: FakeMemory
is tenant-isolated, FakeOrganization is a real (tiny) OU tree with inheritance, FakeAI is
deterministic. Swap a thin adapter around the published sibling to go live.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, TypeVar

from coactra.agent.domain import Scope

T = TypeVar("T")


class FakeAI:
    """Deterministic AIPort: echoes a stable completion; `structured` fills the schema."""

    def ask(self, prompt: str) -> str:
        return f"completion:{prompt}"

    def structured(self, schema: type[T], prompt: str) -> T:
        # Build the schema from defaults where possible; fall back to no-arg construction.
        try:
            return schema()  # type: ignore[call-arg]
        except TypeError:
            # pydantic models with required fields: construct skipping validation so the
            # fake never needs to know the field shapes.
            return schema.model_construct()  # type: ignore[attr-defined, return-value]


class FakeMemory:
    """Tenant-isolated async MemoryPort. recall returns plain dicts (text/score) so the
    fake leaks no sibling type; isolation is keyed on scope.key."""

    def __init__(self) -> None:
        self._store: dict[str, list[str]] = {}

    async def remember(self, events: Sequence[Any], scope: Scope) -> None:
        bucket = self._store.setdefault(scope.key, [])
        for event in events:
            bucket.append(event if isinstance(event, str) else str(event))

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[dict[str, Any]]:
        hits = [t for t in self._store.get(scope.key, []) if query in t]
        return [{"text": t, "score": 1.0} for t in hits[:k]]


class FakeWorkspace:
    """In-memory WorkspacePort. Files are keyed by path; `run` echoes the argv. A Scope is
    bound at construction (mirroring the real Workspace, which binds scope, not per-call)."""

    def __init__(self, scope: Scope | None = None) -> None:
        self._scope = scope
        self._files: dict[str, str] = {}

    def write(self, path: str, data: str) -> None:
        self._files[path] = data

    def read(self, path: str) -> str:
        return self._files.get(path, "")

    def run(self, command: str | Sequence[str]) -> dict[str, Any]:
        argv = command.split() if isinstance(command, str) else list(command)
        return {"argv": argv, "exit_code": 0, "stdout": ""}


class FakeWorkflow:
    """WorkflowPort that records the run and returns a deterministic result. `procedure` is
    treated as a name (str) or any object with a `.name`; state is echoed back."""

    def run(self, procedure: Any, state: dict[str, Any]) -> dict[str, Any]:
        name = procedure if isinstance(procedure, str) else getattr(procedure, "name", str(procedure))
        return {"procedure": name, "state": dict(state), "ran": True}


# --- a tiny, real OU tree behind the OrganizationPort ---------------------------------


@dataclass
class FakeOrgNode:
    """One node in the fake OU tree: a name, a parent, members, and node-level grants."""

    name: str
    parent: "FakeOrgNode | None" = None
    _members: list["FakeMember"] = field(default_factory=list)
    grants: set[str] = field(default_factory=set)

    def add_child(self, name: str) -> "FakeOrgNode":
        return FakeOrgNode(name=name, parent=self)

    def hire(self, name: str, permissions: set[str] | None = None) -> "FakeMember":
        member = FakeMember(name=name, node=self, permissions=set(permissions or set()))
        self._members.append(member)
        return member

    def grant(self, action: str) -> None:
        self.grants.add(action)


@dataclass
class FakeMember:
    """A principal on a FakeOrgNode with its own seat permissions."""

    name: str
    node: FakeOrgNode
    permissions: set[str] = field(default_factory=set)


class FakeOrganization:
    """OrganizationPort over a tiny OU tree with AD-style upward grant inheritance.

    `can(member, action)` is True iff the action is in the member's own permissions OR in
    any node grant on the path from the member's node up to the root. `members(node)` and
    `manager(node)` mirror the real aggregate. This is a faithful (minimal) model, not a
    stub — the inheritance walk is genuinely exercised by tests.
    """

    def can(self, member: FakeMember, action: str) -> bool:
        if action in member.permissions:
            return True
        node: FakeOrgNode | None = member.node
        while node is not None:
            if action in node.grants:
                return True
            node = node.parent
        return False

    def members(self, node: FakeOrgNode) -> list[FakeMember]:
        return list(node._members)

    def manager(self, node: FakeOrgNode) -> FakeOrgNode | None:
        return node.parent


class FakeWork:
    """Tenant-isolated WorkPort fake for dependency-light composition tests."""

    def __init__(self) -> None:
        self._orders: dict[tuple[str, str], Any] = {}

    def submit(self, order: Any) -> Any:
        self._orders[(order.scope.key, order.id)] = order
        return order

    def get(self, work_id: str, scope: Scope) -> Any:
        return self._orders.get((scope.key, work_id))

    def cancel(self, work_id: str, scope: Scope, *, reason: str = "") -> Any:
        order = self.get(work_id, scope)
        if order is not None:
            order.status = "cancelled"
            order.error = reason or None
        return order
