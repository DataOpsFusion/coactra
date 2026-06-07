"""The elegant async Agent facade (Slice 1: model + run/stream/structured)."""
from __future__ import annotations

import uuid
from typing import Any

from coactra.agent.bindings import build_agent_bindings, normalize_agent_skills
from coactra.agent.ports import AgentRuntimePort
from coactra.agent.run import Run
from coactra.agent.runtime import PydanticAIRuntime
from coactra.agent.serve import serve_agent
from coactra.agent.skills import Skill, build_agent_card


class Agent:
    """Elegant async agent facade. Wires model + runtime + memory/workspace/skills."""

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
        self._skills: list[Skill] = skills if skills is not None else []
        self._expose = expose
        self._tools: list[Any] = tools if tools is not None else []

    @classmethod
    async def create(cls, *, model: Any, instructions: str | None = None,
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
                     learned: Any = None,
                     procedure_engine: Any | None = None,
                     procedure_scope: Any | None = None,
                     allow_unreviewed_learned: bool = False,
                     tracer: Any | None = None,
                     **defaults: Any) -> "Agent":
        if runtime is not None:
            skills_for_card = normalize_agent_skills(
                skills,
                learned=learned,
                allow_unreviewed_learned=allow_unreviewed_learned,
            )
            return cls(runtime, name=name, tenant=tenant, skills=skills_for_card, expose=expose)

        bindings = build_agent_bindings(
            tools=tools,
            skills=skills,
            learned=learned,
            allow_unreviewed_learned=allow_unreviewed_learned,
            procedure_engine=procedure_engine,
            procedure_scope=procedure_scope,
            peers=peers,
            registry=registry,
            name=name,
            tenant=tenant,
        )
        rt = PydanticAIRuntime(
            model=model, instructions=instructions, tools=bindings.tools,
            api_base=api_base, api_key=api_key,
            gateway=gateway, auth=auth,
            name=name, tenant=tenant,
            memory=memory, workspace=workspace,
            tracer=tracer,
            mcp_servers=bindings.mcp_servers,
            **defaults,
        )
        return cls(rt, name=name, tenant=tenant, skills=bindings.skills, expose=expose,
                   tools=bindings.tools)

    @property
    def card(self) -> dict | None:
        """Return an A2A Agent Card dict when skills or expose are configured, else None."""
        if not self._skills and not self._expose:
            return None
        return build_agent_card(self._name, self._skills, tenant=self._tenant)

    async def send(self, message: str, *, output: type | None = None,
                   output_type: type | None = None,
                   message_history: list[Any] | None = None) -> Run:
        resolved = output if output is not None else output_type
        return Run(self._runtime, message, run_id=f"run-{uuid.uuid4().hex[:12]}",
                   output_type=resolved, message_history=message_history)

    async def run(self, message: str, *, output: type | None = None,
                  output_type: type | None = None,
                  message_history: list[Any] | None = None) -> Any:
        resolved = output if output is not None else output_type
        result = await (await self.send(message, output_type=resolved,
                                        message_history=message_history)).wait()
        return result.output if resolved is not None else result.text

    def serve(self, *, verifier: Any = None, url: str | None = None) -> Any:
        """Expose this agent as an inbound A2A Starlette app.

        Delegates to :func:`coactra.agent.serve.serve_agent`.  The agent must
        have a non-``None`` :attr:`card` (i.e. at least one skill or
        ``expose=True``); otherwise a ``ValueError`` is raised.

        Parameters
        ----------
        verifier:
            Optional ``A2ARequestVerifier``.  When ``None``, the app runs in
            insecure/unauthenticated mode (suitable for local development).
        url:
            Public A2A endpoint URL to publish in the official Agent Card.

        Returns
        -------
        starlette.applications.Starlette
            A fully assembled Starlette application ready for any ASGI server.
        """
        return serve_agent(self, verifier=verifier, url=url)

    async def aclose(self) -> None:
        """Close any open runtime resources (e.g. gateway httpx client)."""
        if hasattr(self._runtime, "aclose"):
            await self._runtime.aclose()

    async def __aenter__(self) -> "Agent":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
