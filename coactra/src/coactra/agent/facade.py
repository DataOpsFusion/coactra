"""The async Agent facade — a thin composition shell over pydantic-ai.

For direct pydantic-ai access without Coactra memory/workspace/MCP wiring,
import ``pydantic_ai.Agent`` and compose runtime agents through
:class:`coactra.Team`.
"""

from __future__ import annotations

import uuid
from typing import Any

from coactra.agent.bindings import build_agent_bindings
from coactra.agent.ports import AgentRuntimePort
from coactra.agent.run import Run
from coactra.agent.runtime import PydanticAIRuntime
from coactra.agent.skills import Skill, build_agent_card
from coactra.agent.spec import AgentSpec

_KNOWN_RUNTIME_KWARGS = frozenset(
    {
        "api_base",
        "api_key",
        "gateway",
        "auth",
        "name",
        "tenant",
        "memory",
        "workspace",
        "tracer",
        "mcp_servers",
    }
)


class Agent:
    """Thin async facade over pydantic-ai with memory, workspace, MCP, and peer wiring."""

    def __init__(
        self,
        runtime: AgentRuntimePort,
        *,
        name: str | None = None,
        tenant: str | None = None,
        skills: list[Skill] | None = None,
        expose: bool = False,
        tools: list[Any] | None = None,
    ) -> None:
        self._runtime = runtime
        self._name = name or "agent"
        self._tenant = tenant or "default"
        self._skills: list[Skill] = list(skills) if skills is not None else []
        self._expose = expose
        self._tools: list[Any] = list(tools) if tools is not None else []

    @property
    def name(self) -> str:
        return self._name

    @property
    def tenant(self) -> str:
        return self._tenant

    @property
    def skills(self) -> tuple[Skill, ...]:
        return tuple(self._skills)

    def add_skill(self, skill: Skill) -> Skill:
        """Attach a skill unless one with the same id is already present."""
        if not any(existing.id == skill.id for existing in self._skills):
            self._skills.append(skill)
        return skill

    @property
    def card(self) -> dict | None:
        """Return an A2A Agent Card dict when skills or expose are configured, else None."""
        if not self._skills and not self._expose:
            return None
        return build_agent_card(self._name, list(self._skills), tenant=self._tenant)

    async def send(
        self,
        message: str,
        *,
        output: type | None = None,
        output_type: type | None = None,
        message_history: list[Any] | None = None,
    ) -> Run:
        resolved = output if output is not None else output_type
        return Run(
            self._runtime,
            message,
            run_id=f"run-{uuid.uuid4().hex[:12]}",
            output_type=resolved,
            message_history=message_history,
        )

    async def run(
        self,
        message: str,
        *,
        output: type | None = None,
        output_type: type | None = None,
        message_history: list[Any] | None = None,
    ) -> Any:
        resolved = output if output is not None else output_type
        result = await (
            await self.send(message, output_type=resolved, message_history=message_history)
        ).wait()
        return result.output if resolved is not None else result.text

    async def aclose(self) -> None:
        """Close any open runtime resources (e.g. gateway httpx client)."""
        close = getattr(self._runtime, "aclose", None)
        if close is not None:
            await close()

    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()


async def build_agent(spec: AgentSpec, *, policy: Any | None = None) -> Agent:
    """Assemble an Agent from one resolved :class:`coactra.AgentSpec`."""
    unknown = set(spec.defaults) - _KNOWN_RUNTIME_KWARGS
    if unknown:
        raise TypeError(f"build_agent() got unexpected keyword argument(s): {sorted(unknown)}")
    tenant = spec.scope.tenant_id if spec.scope is not None else None
    if spec.runtime is not None:
        return Agent(
            spec.runtime,
            name=spec.name,
            tenant=tenant,
            skills=list(spec.skills),
            expose=spec.expose,
            tools=list(spec.tools),
        )

    bindings = build_agent_bindings(
        tools=list(spec.tools),
        skills=list(spec.skills),
        peers=list(spec.peers),
        registry=spec.registry,
        name=spec.name,
        tenant=tenant,
        policy=policy,
    )
    rt = PydanticAIRuntime(
        model=spec.model,
        instructions=spec.instructions,
        tools=bindings.tools,
        api_base=spec.api_base,
        api_key=spec.api_key,
        gateway=spec.gateway,
        auth=spec.auth,
        name=spec.name,
        tenant=tenant,
        memory=spec.memory,
        workspace=spec.workspace,
        tracer=spec.tracer,
        mcp_servers=bindings.mcp_servers,
        **dict(spec.defaults),
    )
    return Agent(
        rt,
        name=spec.name,
        tenant=tenant,
        skills=bindings.skills,
        expose=spec.expose,
        tools=bindings.tools,
    )
