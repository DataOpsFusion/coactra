"""A pydantic-ai ``Model`` that routes through litellm + coactra.ai's thinking-model
handling. This is the SDK<->ai seam (Slice 2): an agent built with ``Agent.create()``
now gets the same provider routing and ``reasoning_content`` fallback as ``ai.ask``.

Only ``request()`` is implemented (not ``request_stream()``): the SDK's ``stream()``
drives ``agent.iter()`` at the node level and reads the already-resolved
``model_response``, so token-level streaming from the model is not required.
"""
from __future__ import annotations

from typing import Any, Callable, Sequence

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

from coactra.ai.completion.client import _extract_text


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    """Read ``name`` from a dict or an object (litellm responses appear as both)."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class LiteLLMModel(Model):
    """Route pydantic-ai requests through ``litellm.completion``.

    ``model`` is a litellm-style id (``"provider/model"`` or a bare name). ``_completion``
    is injectable for offline tests; in production it lazily resolves to
    ``litellm.completion``.
    """

    def __init__(
        self,
        model: str,
        *,
        api_base: str | None = None,
        api_key: str | None = None,
        settings: ModelSettings | None = None,
        _completion: Callable[..., Any] | None = None,
        **defaults: Any,
    ) -> None:
        super().__init__(settings=settings)
        self._provider = None  # no HTTP client to manage; disables Model.__aenter__ work
        self._model_id = model
        self._completion = _completion
        self._call_kwargs: dict[str, Any] = dict(defaults)
        if api_base is not None:
            self._call_kwargs["api_base"] = api_base
        if api_key is not None:
            self._call_kwargs["api_key"] = api_key

    @property
    def model_name(self) -> str:
        return self._model_id

    @property
    def system(self) -> str:
        return self._model_id.split("/", 1)[0] if "/" in self._model_id else "litellm"

    def _completion_fn(self) -> Callable[..., Any]:
        if self._completion is None:
            import litellm  # local import: only the litellm path needs the dependency

            self._completion = litellm.completion
        return self._completion

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        kwargs = dict(self._call_kwargs)
        if tools := self._map_tools(model_request_parameters):
            # No forced `tool_choice`: required-mode rejects thinking models, which is the
            # very class of model this seam exists to support. Output tools are still
            # selected via the prompt pydantic-ai sends; weak picks degrade to a retry.
            kwargs["tools"] = tools
        response = self._completion_fn()(
            model=self._model_id, messages=self._map_messages(messages), **kwargs
        )
        return self._process_response(response)

    @staticmethod
    def _map_tools(params: ModelRequestParameters) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {
                "name": d.name, "description": d.description or "",
                "parameters": d.parameters_json_schema}}
            for d in (*params.function_tools, *params.output_tools)
        ]

    def _map_messages(self, messages: Sequence[ModelMessage]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for message in messages:
            if isinstance(message, ModelRequest):
                out.extend(self._map_request(message))
            elif isinstance(message, ModelResponse):
                out.append(self._map_response(message))
        return out

    @staticmethod
    def _map_request(message: ModelRequest) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for part in message.parts:
            if isinstance(part, SystemPromptPart):
                out.append({"role": "system", "content": part.content})
            elif isinstance(part, UserPromptPart):
                out.append({"role": "user", "content": part.content})
            elif isinstance(part, ToolReturnPart):
                out.append({"role": "tool", "tool_call_id": part.tool_call_id,
                            "content": part.model_response_str()})
            elif isinstance(part, RetryPromptPart):
                if part.tool_name is None:
                    out.append({"role": "user", "content": part.model_response()})
                else:
                    out.append({"role": "tool", "tool_call_id": part.tool_call_id,
                                "content": part.model_response()})
        return out

    @staticmethod
    def _map_response(message: ModelResponse) -> dict[str, Any]:
        text = "".join(p.content for p in message.parts if isinstance(p, TextPart))
        tool_calls = [
            {"id": p.tool_call_id, "type": "function",
             "function": {"name": p.tool_name, "arguments": p.args_as_json_str()}}
            for p in message.parts if isinstance(p, ToolCallPart)
        ]
        out: dict[str, Any] = {"role": "assistant", "content": text or None}
        if tool_calls:
            out["tool_calls"] = tool_calls
        return out

    def _process_response(self, response: Any) -> ModelResponse:
        message = _attr(_attr(response, "choices", [{}])[0], "message", {})
        tool_calls = _attr(message, "tool_calls") or []
        # `reasoning_content` is the answer only when there is no tool call; on a tool turn
        # it is genuine thinking and must not be emitted as text output.
        text = (_attr(message, "content") or "") if tool_calls else _extract_text(message)
        reasoning = _attr(message, "reasoning_content") or _attr(message, "reasoning")
        parts: list[ModelResponsePart] = []
        if reasoning and reasoning != text:
            parts.append(ThinkingPart(reasoning))
        if text:
            parts.append(TextPart(text))
        for call in tool_calls:
            fn = _attr(call, "function", {})
            cid = _attr(call, "id")
            name = _attr(fn, "name") or ""
            args = _attr(fn, "arguments")
            parts.append(ToolCallPart(name, args, tool_call_id=cid) if cid else ToolCallPart(name, args))
        return ModelResponse(parts=parts, usage=self._map_usage(response), model_name=self._model_id)

    @staticmethod
    def _map_usage(response: Any) -> RequestUsage:
        usage = _attr(response, "usage")
        if usage is None:
            return RequestUsage()
        return RequestUsage(
            input_tokens=_attr(usage, "prompt_tokens", 0) or 0,
            output_tokens=_attr(usage, "completion_tokens", 0) or 0,
        )
