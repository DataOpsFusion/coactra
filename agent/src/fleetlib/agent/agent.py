"""Agent — the clean, wrappable facade. Thin composition over injected ports + the three
session subsystems (mounting, identity, collaboration).

It is DELIBERATELY thin: every capability call delegates to an injected port or a built
subsystem; the Agent re-implements NONE of memory/workflow/workspace/ai/organization
behavior. A mandatory Scope threads into every subsystem so isolation is real. The surface
is small and typed so an openai-sdk tool or an a2a skill can wrap it in a few lines;
`remember`/`recall` are async because the underlying memory protocol is async.

Construct via the `make_agent` composition root (factory.py) — nothing is instantiated
inline in this class; everything arrives through the constructor.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

from fleetlib.agent.collaboration import (
    AgentRef,
    CollaborationPolicy,
    PolicyGatedCollaborator,
)
from fleetlib.agent.domain import DelegationGrant, ExchangedIdentity, Scope, ToolSpec
from fleetlib.agent.identity import TokenExchanger
from fleetlib.agent.mounting import MCPServerPort, MountRegistry
from fleetlib.agent.ports import (
    AIPort,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
)

T = TypeVar("T")


class Agent:
    """One scoped agent: ports + the three session subsystems, wired by the factory.

    Prefer `make_agent(...)` to construct one; this constructor takes already-built
    collaborators/registries so the class instantiates nothing itself.
    """

    def __init__(
        self,
        *,
        scope: Scope,
        me: str,
        ai: AIPort,
        memory: MemoryPort,
        workspace: WorkspacePort,
        workflow: WorkflowPort,
        organization: OrganizationPort,
        exchanger: TokenExchanger,
        mounts: MountRegistry,
        collaborator: PolicyGatedCollaborator,
        policy: CollaborationPolicy,
    ) -> None:
        self.scope = scope
        self._me = me
        self._ai = ai
        self._memory = memory
        self._workspace = workspace
        self._workflow = workflow
        self._org = organization
        self._exchanger = exchanger
        self._mounts = mounts
        self._collaborator = collaborator
        self._policy = policy

    @property
    def me(self) -> str:
        return self._me

    # --- (1) mid-session mounting -----------------------------------------------------

    def mount_mcp(
        self, mount_id: str, server: MCPServerPort, *, effective: str = "next_turn"
    ) -> None:
        """Stage an MCP server; its tools become visible on the next begin_turn()."""
        if effective != "next_turn":
            raise ValueError("only effective='next_turn' is supported")
        self._mounts.stage(mount_id, server)

    def begin_turn(self) -> None:
        """The safe-turn boundary: promote staged mounts and invalidate the tool cache."""
        self._mounts.begin_turn()

    def tools_specs(self) -> list[ToolSpec]:
        return self._mounts.active_tools()

    def tools(self) -> list[str]:
        return [t.qualified_name for t in self._mounts.active_tools()]

    def tools_of(self, mount_id: str) -> list[str]:
        """Active tools contributed by one mount (O(prefix) trie subtree walk)."""
        return [t.qualified_name for t in self._mounts.tools_under(mount_id)]

    # --- (2) delegated identity -------------------------------------------------------

    def act_on_behalf_of(self, grant: DelegationGrant) -> ExchangedIdentity:
        """RFC 8693 exchange — fresh downstream identity, never the raw subject token."""
        return self._exchanger.exchange(grant, self.scope)

    def delegate_further(
        self, identity: ExchangedIdentity, *, actor: str
    ) -> ExchangedIdentity:
        """Multi-hop delegation — append one hop to the immutable actor chain (still no
        passthrough). Goes through the TokenExchanger Protocol, so it works with any
        exchanger (in-process default OR KeycloakExchanger)."""
        return self._exchanger.exchange_from(identity, actor=actor, scope=self.scope)

    # --- (3) collaboration ------------------------------------------------------------

    def can_talk(self, dst: str | AgentRef) -> bool:
        me_ref = AgentRef(tenant_id=self.scope.tenant_id, agent_id=self._me)
        return self._policy.can_talk(me_ref, dst, self.scope)

    def talk(self, dst: str | AgentRef, question: str) -> str:
        """Ask another agent over the gated A2A transport (raises CollaborationDenied)."""
        return self._collaborator.ask(dst, question, {})

    @property
    def collaborator(self) -> PolicyGatedCollaborator:
        """The workflow-compatible Collaborator/EscalationRouter — drops into a RunContext."""
        return self._collaborator

    # --- sibling delegating shims (thin: just forward to the port) --------------------

    def think(self, prompt: str) -> str:
        return self._ai.ask(prompt)

    def think_structured(self, schema: type[T], prompt: str) -> T:
        return self._ai.structured(schema, prompt)

    async def remember(self, events: Sequence[Any]) -> None:
        """Persist conversational events into scoped memory (async — memory is async)."""
        await self._memory.remember(events, self.scope)

    async def recall(self, query: str, *, k: int = 10) -> list[Any]:
        """Recall the top-k recollections for `query` within scope (async)."""
        return await self._memory.recall(query, self.scope, k)

    def workspace_write(self, path: str, content: str) -> None:
        self._workspace.write(path, content)

    def workspace_read(self, path: str) -> str:
        return self._workspace.read(path)

    def workspace_run(self, command: str | Sequence[str]) -> Any:
        return self._workspace.run(command)

    def run_procedure(self, procedure: Any, state: dict[str, Any] | None = None) -> Any:
        """Run a workflow procedure; the workflow adapter threads this agent's own
        policy-gated collaborator in, so `ask` steps talk back through agent policy."""
        return self._workflow.run(procedure, state or {})

    def can(self, member: Any, action: Any) -> bool:
        """Permission check delegated to the organization port (AD-style resolution)."""
        return self._org.can(member, action)

    def manager_of(self, node: Any) -> Any:
        """The escalation target one tier up for `node` (organization port)."""
        return self._org.manager(node)

    def members_of(self, node: Any) -> list[Any]:
        return self._org.members(node)
