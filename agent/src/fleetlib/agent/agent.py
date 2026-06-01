"""Agent — the thin composition root that wires the three subsystems + five sibling ports.

It is DELIBERATELY thin: every capability call delegates to an injected port or a built
subsystem; the Agent re-implements NONE of memory/workflow/workspace behavior. A mandatory
Scope threads into every subsystem so isolation is real, not bolted on. Defaults are the
in-process fakes/working-defaults, so an Agent works out of the box; advanced users inject
real adapters (fastmcp/a2a/keycloak + published siblings).
"""

from __future__ import annotations

from fleetlib.agent.collaboration import (
    A2ATransportPort,
    AgentRef,
    AllowSameTenant,
    CollaborationPolicy,
    PolicyGatedCollaborator,
)
from fleetlib.agent.delegation import (
    DelegationGrant,
    ExchangedIdentity,
    InProcessExchanger,
    TokenExchanger,
)
from fleetlib.agent.mounting import ConflictPolicy, MCPServerPort, MountRegistry
from fleetlib.agent.ports import (
    AIPort,
    FakeAI,
    FakeMemory,
    FakeOrganization,
    FakeWorkflow,
    FakeWorkspace,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
)
from fleetlib.agent.scope import Scope
from fleetlib.agent.tools import ToolSpec


class Agent:
    """Composition/policy layer: one agent, scoped, wiring protocols + sibling ports."""

    def __init__(
        self,
        *,
        scope: Scope,
        me: str,
        ai: AIPort | None = None,
        memory: MemoryPort | None = None,
        workspace: WorkspacePort | None = None,
        workflow: WorkflowPort | None = None,
        organization: OrganizationPort | None = None,
        transport: A2ATransportPort | None = None,
        collaboration_policy: CollaborationPolicy | None = None,
        exchanger: TokenExchanger | None = None,
        conflict_policy: ConflictPolicy | None = None,
    ) -> None:
        self.scope = scope
        self._me = me
        self._ai: AIPort = ai or FakeAI()
        self._memory: MemoryPort = memory or FakeMemory()
        self._workspace: WorkspacePort = workspace or FakeWorkspace()
        self._workflow: WorkflowPort = workflow or FakeWorkflow()
        self._org: OrganizationPort = organization or FakeOrganization()
        self._exchanger: TokenExchanger = exchanger or InProcessExchanger()
        self._mounts = MountRegistry(scope=scope, conflict_policy=conflict_policy)
        # ONE policy instance, shared by can_talk() and the gated collaborator (no drift).
        self._policy: CollaborationPolicy = collaboration_policy or AllowSameTenant()
        self._collaborator = PolicyGatedCollaborator(
            transport=transport or _NullTransport(),
            policy=self._policy,
            scope=scope,
            me=me,
        )

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

    # --- (2) delegated identity -------------------------------------------------------

    def act_on_behalf_of(self, grant: DelegationGrant) -> ExchangedIdentity:
        """RFC 8693 exchange — fresh downstream identity, never the raw subject token."""
        return self._exchanger.exchange(grant, self.scope)

    def delegate_further(self, identity: ExchangedIdentity, *, actor: str) -> ExchangedIdentity:
        """Multi-hop delegation — extend the nested actor chain by one hop (still no
        passthrough). Goes through the TokenExchanger Protocol, so it works with any
        exchanger (in-process default OR KeycloakExchanger)."""
        return self._exchanger.exchange_from(identity, actor=actor, scope=self.scope)

    # --- (3) collaboration ------------------------------------------------------------

    def can_talk(self, dst: str | AgentRef) -> bool:
        return self._policy.can_talk(self._me, dst, self.scope)

    def ask(self, dst: str | AgentRef, question: str) -> str:
        return self._collaborator.ask(dst, question, {})

    @property
    def collaborator(self) -> PolicyGatedCollaborator:
        """The workflow-compatible Collaborator/EscalationRouter for use in a RunContext."""
        return self._collaborator

    # --- sibling delegating shims (thin: just forward to the port) --------------------

    def think(self, prompt: str) -> str:
        return self._ai.complete(prompt)

    def memory(self, text: str) -> None:
        self._memory.learn(text, self.scope)

    def recall(self, query: str) -> list[str]:
        return self._memory.recall(query, self.scope)

    def workspace_write(self, path: str, content: str) -> None:
        self._workspace.write(path, content, self.scope)

    def workspace_read(self, path: str) -> str:
        return self._workspace.read(path, self.scope)

    def run_procedure(self, name: str) -> dict:
        return self._workflow.run(name, self.scope)

    def escalation_chain(self) -> list[str]:
        return self._org.escalation_chain(self._me, self.scope)


class _NullTransport:
    """Default A2A transport — no wire configured; records nothing, returns empty."""

    def send(self, dst: AgentRef, question: str, scope: Scope) -> str:
        return ""
