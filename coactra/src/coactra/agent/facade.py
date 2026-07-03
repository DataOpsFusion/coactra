"""The async Agent facade — a thin composition shell over pydantic-ai.

For direct pydantic-ai access without Coactra memory/workspace/MCP wiring,
import ``pydantic_ai.Agent`` and compose runtime agents through
:class:`coactra.Team`.
"""

from __future__ import annotations

import uuid
from typing import Any

from coactra.agent.bindings import build_agent_bindings, normalize_agent_skills
from coactra.agent.ports import AgentRuntimePort
from coactra.agent.run import Run
from coactra.agent.runtime import PydanticAIRuntime
from coactra.agent.skills import Skill, build_agent_card

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


async def build_agent(
    *,
    model: Any,
    instructions: str | None = None,
    tools: list[Any] | None = None,
    runtime: AgentRuntimePort | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    gateway: str | None = None,
    auth: Any = None,
    name: str | None = None,
    tenant: str | None = None,
    memory: Any = None,
    workspace: Any = None,
    skills: Any = None,
    expose: bool = False,
    peers: list | None = None,
    registry: Any | None = None,
    tracer: Any | None = None,
    policy: Any | None = None,
    **defaults: Any,
) -> Agent:
    """Internal Team-facing agent assembly helper."""
    unknown = set(defaults) - _KNOWN_RUNTIME_KWARGS
    if unknown:
        raise TypeError(f"build_agent() got unexpected keyword argument(s): {sorted(unknown)}")
    if runtime is not None:
        skills_for_card = normalize_agent_skills(skills)
        return Agent(runtime, name=name, tenant=tenant, skills=skills_for_card, expose=expose)

    bindings = build_agent_bindings(
        tools=tools,
        skills=skills,
        peers=peers,
        registry=registry,
        name=name,
        tenant=tenant,
        policy=policy,
    )
    rt = PydanticAIRuntime(
        model=model,
        instructions=instructions,
        tools=bindings.tools,
        api_base=api_base,
        api_key=api_key,
        gateway=gateway,
        auth=auth,
        name=name,
        tenant=tenant,
        memory=memory,
        workspace=workspace,
        tracer=tracer,
        mcp_servers=bindings.mcp_servers,
        **defaults,
    )
    return Agent(
        rt,
        name=name,
        tenant=tenant,
        skills=bindings.skills,
        expose=expose,
        tools=bindings.tools,
    )
