"""The five sibling PORTS — the un-tangling seam.

agent wires ai/memory/workspace/workflow/organization, but consuming a sibling's CODE
would re-tangle the libraries. So each sibling is consumed through a NARROW local port
Protocol. Each port is shaped to MIRROR the real sibling facade, so the downstream wiring
is a 3-line adapter rather than glue:

  - MemoryPort.remember(events, scope) / recall(query, scope, k)   <- fleetlib.memory.Memory (ASYNC)
  - OrganizationPort.can(member, action) / members(node) / manager(node)  <- fleetlib.organization.Organization
  - AIPort.ask(prompt) / structured(schema, prompt)                <- fleetlib.ai
  - WorkflowPort.run(procedure, state)                             <- fleetlib.workflow (engine + RunContext)
  - WorkspacePort.read / write / run                               <- fleetlib.workspace.Workspace

This library never imports `fleetlib.<sibling>`; structural typing is the only contract.
Only `MemoryPort` is async — its real facade (`Memory.remember`/`recall`) is async. The
rest mirror sync facades. Generics (member/node/procedure/schema) are intentionally
untyped at the port: each is an opaque sibling type the agent never inspects.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, TypeVar, runtime_checkable

from fleetlib.agent.domain import Scope

T = TypeVar("T")


@runtime_checkable
class AIPort(Protocol):
    def ask(self, prompt: str) -> str:
        """Free-text model completion (mirrors fleetlib.ai.ask)."""
        ...

    def structured(self, schema: type[T], prompt: str) -> T:
        """Typed model output validated against `schema` (mirrors fleetlib.ai.structured)."""
        ...


@runtime_checkable
class MemoryPort(Protocol):
    async def remember(self, events: Sequence[Any], scope: Scope) -> None:
        """Persist conversational events within scope (mirrors fleetlib.memory.remember)."""
        ...

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Any]:
        """Recall the top-k recollections for `query` within scope (mirrors recall)."""
        ...


@runtime_checkable
class WorkspacePort(Protocol):
    def write(self, path: str, data: str) -> None:
        """Write a file to the agent's persistent desk (mirrors Workspace.write)."""
        ...

    def read(self, path: str) -> str:
        """Read a file from the desk (mirrors Workspace.read)."""
        ...

    def run(self, command: str | Sequence[str]) -> Any:
        """Run a policy-gated command on the desk (mirrors Workspace.run -> ExecResult)."""
        ...


@runtime_checkable
class WorkflowPort(Protocol):
    def run(self, procedure: Any, state: dict[str, Any]) -> Any:
        """Compile + execute a procedure with `state` (mirrors fleetlib.workflow run).

        The narrow surface is `(procedure, state)`; an adapter supplies the sibling's
        `RunContext` (scope + the agent's own collaborator/router) so a workflow `ask`
        step talks back through the agent's policy-gated collaborator.
        """
        ...


@runtime_checkable
class OrganizationPort(Protocol):
    def can(self, member: Any, action: Any) -> bool:
        """True iff `member` is permitted `action` (mirrors Organization.can)."""
        ...

    def members(self, node: Any) -> list[Any]:
        """The members of an org node (mirrors Organization.members)."""
        ...

    def manager(self, node: Any) -> Any:
        """The escalation target one tier up — the node's parent (mirrors .manager)."""
        ...
