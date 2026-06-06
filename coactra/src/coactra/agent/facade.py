"""The elegant async Agent facade (Slice 1: model + run/stream/structured)."""
from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from coactra.agent.events import Event, RunResult
from coactra.agent.peers import peer_tools
from coactra.agent.runtime import AgentRuntimePort, PydanticAIRuntime
from coactra.agent.serve import serve_agent
from coactra.agent.skills import Skill, build_agent_card, normalize_skills


class Run:
    """A handle to one send(). Stream events OR await the final result (not both-consuming:
    wait() runs to completion; stream() yields events and also captures the final result)."""

    def __init__(self, runtime: AgentRuntimePort, prompt: str, *, run_id: str,
                 output_type: type | None, message_history: list[Any] | None) -> None:
        self._runtime = runtime
        self._prompt = prompt
        self.id = run_id
        self._output_type = output_type
        self._history = message_history
        self._result: RunResult | None = None

    async def stream(self) -> AsyncIterator[Event]:
        def _capture(result: RunResult) -> None:
            if self._result is None:
                self._result = result

        async for ev in self._runtime.stream(
            self._prompt, run_id=self.id, output_type=self._output_type,
            message_history=self._history, on_result=_capture,
        ):
            yield ev

    async def wait(self) -> RunResult:
        if self._result is None:
            self._result = await self._runtime.run(
                self._prompt, run_id=self.id, output_type=self._output_type,
                message_history=self._history,
            )
        return self._result


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
                     **defaults: Any) -> "Agent":
        combined_tools: list[Any] = list(tools) if tools is not None else []
        if peers:
            _resolver = {p._name: p for p in peers}.get
            combined_tools = combined_tools + peer_tools(
                [p._name for p in peers],
                resolve=_resolver,
                me=name,
                tenant=tenant,
            )
        if runtime is not None:
            rt = runtime
        else:
            rt = PydanticAIRuntime(
                model=model, instructions=instructions, tools=combined_tools,
                api_base=api_base, api_key=api_key,
                gateway=gateway, auth=auth,
                name=name, tenant=tenant,
                memory=memory, workspace=workspace,
                skills=skills, expose=expose,
                **defaults,
            )
        normalised_skills = normalize_skills(skills)
        return cls(rt, name=name, tenant=tenant, skills=normalised_skills, expose=expose,
                   tools=combined_tools)

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

    def serve(self, *, verifier: Any = None) -> Any:
        """Expose this agent as an inbound A2A Starlette app.

        Delegates to :func:`coactra.agent.serve.serve_agent`.  The agent must
        have a non-``None`` :attr:`card` (i.e. at least one skill or
        ``expose=True``); otherwise a ``ValueError`` is raised.

        Parameters
        ----------
        verifier:
            Optional ``A2ARequestVerifier``.  When ``None``, the app runs in
            insecure/unauthenticated mode (suitable for local development).

        Returns
        -------
        starlette.applications.Starlette
            A fully assembled Starlette application ready for any ASGI server.
        """
        return serve_agent(self, verifier=verifier)

    async def aclose(self) -> None:
        """Close any open runtime resources (e.g. gateway httpx client)."""
        if hasattr(self._runtime, "aclose"):
            await self._runtime.aclose()

    async def __aenter__(self) -> "Agent":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
