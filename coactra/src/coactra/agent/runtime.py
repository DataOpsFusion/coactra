"""Default pydantic-ai backed agent runtime."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import nullcontext
from typing import Any

from pydantic_ai import Agent as PydAgent

from coactra.agent.events import RunResult, Status, ToolCall
from coactra.agent.ports import AgentRuntimePort
from coactra.agent.runtime_events import iter_call_tools_node_events
from coactra.agent.runtime_wiring import (
    bind_runtime_memory,
    bind_runtime_workspace,
    close_workspace,
)

__all__ = ["AgentRuntimePort", "PydanticAIRuntime"]

logger = logging.getLogger(__name__)


def _resolve_model(
    model: Any,
    *,
    api_base: str | None,
    api_key: str | None,
    defaults: dict[str, Any],
) -> Any:
    if (api_base is not None or api_key is not None or defaults) and isinstance(model, str):
        logger.warning(
            "api_base, api_key, and extra model kwargs are ignored for string model "
            "ids; pass a pydantic-ai Model instance to configure provider credentials"
        )
    return model


def _usage(result: Any, run_id: str, *, seq: int = 0):
    try:
        usage = result.usage
        tokens = getattr(usage, "total_tokens", 0) or (
            (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "output_tokens", 0) or 0)
        )
        from coactra.agent.events import Usage  # noqa: PLC0415

        return Usage(run_id=run_id, seq=seq, tokens=tokens)
    except Exception:
        return None


class PydanticAIRuntime:
    """Default runtime for pydantic-ai model instances or provider strings."""

    def __init__(
        self,
        *,
        model: Any,
        instructions: str | None = None,
        tools: list[Any] | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        gateway: str | None = None,
        auth: Any = None,
        name: str | None = None,
        tenant: str | None = None,
        memory: Any = None,
        workspace: Any = None,
        tracer: Any | None = None,
        mcp_servers: list[Any] | None = None,
        **defaults: Any,
    ) -> None:
        self._model = _resolve_model(
            model,
            api_base=api_base,
            api_key=api_key,
            defaults=defaults,
        )
        self._instructions = instructions
        self._tools = tools or []
        self._agent_name = name or "agent"
        self._tenant_name = tenant or "default"
        self._tracer = tracer

        from coactra.agent.toolsets import build_mcp_toolsets  # noqa: PLC0415

        self._gateway_toolset, self._mcp_toolsets = build_mcp_toolsets(
            gateway=gateway,
            auth=auth,
            mcp_servers=mcp_servers,
        )
        self._gateway_url: str | None = gateway
        self._memory = bind_runtime_memory(
            memory,
            tenant=self._tenant_name,
            agent=self._agent_name,
        )
        self._workspace, self._workspace_tools = bind_runtime_workspace(
            workspace,
            tenant=self._tenant_name,
            agent=self._agent_name,
        )

    def _build(self, output_type: type | None):
        toolsets = []
        if self._gateway_toolset is not None:
            toolsets.append(self._gateway_toolset)
        toolsets.extend(self._mcp_toolsets)
        kwargs: dict[str, Any] = {
            "instructions": self._instructions,
            "tools": [*self._tools, *self._workspace_tools],
        }
        if output_type is not None:
            kwargs["output_type"] = output_type
        if toolsets:
            kwargs["toolsets"] = toolsets
        return PydAgent(self._model, **kwargs)

    async def aclose(self) -> None:
        """Close runtime-owned resources."""
        await close_workspace(self._workspace)

    def _usage(self, result: Any, run_id: str, *, seq: int = 0):
        return _usage(result, run_id, seq=seq)

    def _span(self, name: str, run_id: str):
        if self._tracer is None:
            return nullcontext(None)
        return self._tracer.start_as_current_span(
            name,
            attributes={
                "coactra.run_id": run_id,
                "coactra.agent.name": self._agent_name,
                "coactra.tenant_id": self._tenant_name,
            },
        )

    async def _recall(self, prompt: str) -> str:
        if self._memory is None:
            return prompt
        recalled = await self._memory.recall(prompt)
        if not recalled:
            return prompt
        return f"Relevant context:\n{recalled}\n\n{prompt}"

    async def _remember(self, prompt: str, text: str) -> None:
        if self._memory is not None:
            await self._memory.remember(f"user: {prompt}\nassistant: {text}")

    @staticmethod
    def _public_output(output: Any, output_type: type | None) -> tuple[str, Any]:
        text = output if isinstance(output, str) else ""
        public_output = (
            output if output_type is not None else (None if isinstance(output, str) else output)
        )
        return text, public_output

    async def run(
        self,
        prompt: str,
        *,
        run_id: str,
        output_type: type | None = None,
        message_history: list[Any] | None = None,
    ) -> RunResult:
        with self._span("coactra.agent.run", run_id) as span:
            original_prompt = prompt
            prompt = await self._recall(prompt)
            if span is not None:
                span.add_event(
                    "coactra.model.request",
                    attributes={"coactra.prompt.length": len(prompt)},
                )
            result = await self._build(output_type).run(
                prompt,
                message_history=message_history,
            )
            output = result.output
            text, public_output = self._public_output(output, output_type)
            if span is not None:
                span.add_event(
                    "coactra.model.response",
                    attributes={
                        "coactra.output.type": type(output).__name__,
                        "coactra.output.length": len(text),
                    },
                )
            await self._remember(original_prompt, text)
            return RunResult.finished(
                text=text,
                output=public_output,
                usage=self._usage(result, run_id),
                messages=tuple(result.all_messages()),
            )

    async def stream(
        self,
        prompt: str,
        *,
        run_id: str,
        output_type: type | None = None,
        message_history: list[Any] | None = None,
        on_result: Callable[[RunResult], None] | None = None,
    ):
        """Drive the pydantic-ai agent graph and yield coactra event DTOs."""
        seq = 0
        with self._span("coactra.agent.stream", run_id) as span:
            original_prompt = prompt
            prompt = await self._recall(prompt)
            if span is not None:
                span.add_event(
                    "coactra.model.request",
                    attributes={"coactra.prompt.length": len(prompt)},
                )
            tool_calls: list[ToolCall] = []
            try:
                async with self._build(output_type).iter(
                    prompt,
                    message_history=message_history,
                ) as run:
                    async for node in run:
                        if PydAgent.is_call_tools_node(node):
                            async for event, next_seq in iter_call_tools_node_events(
                                node,
                                run.ctx,
                                run_id=run_id,
                                seq=seq,
                                tool_calls=tool_calls,
                            ):
                                yield event
                                seq = next_seq
                    result = run.result
                    usage = self._usage(result, run_id, seq=seq) if result is not None else None
                    if usage is not None:
                        yield usage
                        seq += 1
                    if result is not None:
                        output = result.output
                        text, public_output = self._public_output(output, output_type)
                        if span is not None:
                            span.add_event(
                                "coactra.model.response",
                                attributes={
                                    "coactra.output.type": type(output).__name__,
                                    "coactra.output.length": len(text),
                                },
                            )
                        await self._remember(original_prompt, text)
                        if on_result is not None:
                            on_result(
                                RunResult.finished(
                                    text=text,
                                    output=public_output,
                                    usage=usage,
                                    tool_calls=tuple(tool_calls),
                                    messages=tuple(result.all_messages()),
                                )
                            )
            except Exception as exc:  # noqa: BLE001 - terminal error event is the contract
                logger.exception("agent stream failed", extra={"coactra_run_id": run_id})
                yield Status(run_id=run_id, seq=seq, state="error")
                if on_result is not None:
                    on_result(RunResult.failed(str(exc)))
                return
            yield Status(run_id=run_id, seq=seq, state="finished")
