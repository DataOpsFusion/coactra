"""Agent facade binding helpers.

These helpers keep Agent.create focused on composition. They normalize user-facing
Agent.create inputs into runtime-ready skills, local tools, and additive MCP servers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from coactra.agent.domain import AgentRef
from coactra.agent.domain.tools import MCPServer
from coactra.agent.learned import (
    learned_procedure_skills,
    learned_procedure_tools,
    normalize_learned_procedures,
)
from coactra.agent.peers import RemotePeer, peer_tools
from coactra.agent.skills import Skill, normalize_skills


@dataclass(frozen=True)
class AgentBindings:
    """Runtime-ready pieces derived from Agent.create inputs."""

    skills: list[Skill]
    tools: list[Any]
    mcp_servers: list[MCPServer]


def build_agent_bindings(
    *,
    tools: list[Any] | None,
    skills: Any,
    learned: Any,
    allow_unreviewed_learned: bool,
    procedure_engine: Any | None,
    procedure_scope: Any | None,
    peers: list[Any] | None,
    registry: Any | None,
    name: str | None,
    tenant: str | None,
) -> AgentBindings:
    """Normalize Agent.create inputs into skills, callable tools, and MCP tags."""
    learned_procedures = normalize_learned_procedures(
        learned, allow_unreviewed=allow_unreviewed_learned
    )
    normalized_skills = agent_skills(skills, learned_procedures)
    local_tools, mcp_servers = split_mcp_tools(tools)
    bound_tools = [
        *local_tools,
        *learned_procedure_tools(
            learned_procedures,
            engine=procedure_engine,
            tenant=tenant,
            scope=procedure_scope,
        ),
        *bind_peer_tools(peers=peers, registry=registry, name=name, tenant=tenant),
    ]
    return AgentBindings(skills=normalized_skills, tools=bound_tools, mcp_servers=mcp_servers)


def normalize_agent_skills(
    skills: Any,
    *,
    learned: Any,
    allow_unreviewed_learned: bool,
) -> list[Skill]:
    procedures = normalize_learned_procedures(learned, allow_unreviewed=allow_unreviewed_learned)
    return agent_skills(skills, procedures)


def agent_skills(skills: Any, learned_procedures: list[Any]) -> list[Skill]:
    return normalize_skills(skills) + learned_procedure_skills(learned_procedures)


def split_mcp_tools(tools: list[Any] | None) -> tuple[list[Any], list[MCPServer]]:
    """Separate local callable tools from public mcp() server tags."""
    local_tools: list[Any] = []
    mcp_servers: list[MCPServer] = []
    for tool in tools or []:
        if isinstance(tool, MCPServer):
            mcp_servers.append(tool)
        else:
            local_tools.append(tool)
    return local_tools, mcp_servers


def bind_peer_tools(
    *,
    peers: list[Any] | None,
    registry: Any | None,
    name: str | None,
    tenant: str | None,
) -> list[Any]:
    """Build peer delegation tools from local agents, names, and remote entries."""
    if not peers:
        return []

    local_agents, named_peers, direct_remotes = classify_peers(peers)
    registry_remotes, unresolved_names = resolve_named_remotes(
        named_peers, registry=registry, tenant=tenant
    )

    tools: list[Any] = []
    if local_agents:
        resolver = {p._name: p for p in local_agents}.get
        tools.extend(
            peer_tools(
                [p._name for p in local_agents],
                resolve=resolver,
                me=name,
                tenant=tenant,
            )
        )
    if unresolved_names:
        tools.extend(
            peer_tools(
                unresolved_names,
                resolve=lambda _name: None,
                me=name,
                tenant=tenant,
            )
        )
    for remote in [*direct_remotes, *registry_remotes]:
        tools.extend(
            peer_tools(
                [
                    AgentRef(
                        tenant_id=remote.tenant or tenant or "default",
                        agent_id=remote.name,
                    )
                ],
                resolve=lambda _name: None,
                transport=remote.transport(),
                me=name,
                tenant=tenant,
            )
        )
    return tools


def classify_peers(peers: list[Any]) -> tuple[list[Any], list[str], list[RemotePeer]]:
    local_agents: list[Any] = []
    named_peers: list[str] = []
    direct_remotes: list[RemotePeer] = []
    local_names: set[str] = set()

    for peer in peers:
        if isinstance(peer, RemotePeer):
            direct_remotes.append(peer)
        elif isinstance(peer, str):
            named_peers.append(peer)
        elif hasattr(peer, "_name"):
            peer_name = str(peer._name)
            if peer_name in local_names:
                raise ValueError(f"duplicate local peer name: {peer_name!r}")
            local_names.add(peer_name)
            local_agents.append(peer)
        else:
            raise TypeError(
                "peers must contain Agent-like objects, peer names, or RemotePeer configs"
            )

    return local_agents, named_peers, direct_remotes


def resolve_named_remotes(
    names: list[str],
    *,
    registry: Any | None,
    tenant: str | None,
) -> tuple[list[RemotePeer], list[str]]:
    if registry is None or not names:
        return [], names

    remotes: list[RemotePeer] = []
    unresolved: list[str] = []
    for peer_name in names:
        entry = registry.resolve(peer_name, tenant=tenant)
        if entry is None:
            unresolved.append(peer_name)
        else:
            remotes.append(entry.remote_peer())
    return remotes, unresolved
