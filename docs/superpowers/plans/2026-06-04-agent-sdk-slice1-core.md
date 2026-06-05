# Agent SDK — Slice 1 (elegant core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the elegant async `Agent` core — `Agent.create / send / run / run(output_type=) / stream / aclose` — backed by pydantic-ai, fully testable offline. No MCP/A2A/memory wiring yet (those are later slices); model is selected from the `model=` string using pydantic-ai's native providers.

**Architecture:** A new `coactra/agent/sdk/` subpackage in the `coactra-agent` package. `PydanticAIRuntime` (implementing an `AgentRuntimePort` Protocol) builds a `pydantic_ai.Agent` and maps its result/stream to coactra event DTOs. The public `Agent` facade is a thin async wrapper exposing `create/send/run/stream/aclose`. Existing `make_agent` / `coactra.agent.Agent` are untouched.

**Tech Stack:** Python 3.12, pydantic-ai (`pydantic-ai-slim`), pytest + pytest-asyncio. Offline tests use pydantic-ai's `TestModel` / `FunctionModel` via `Agent.override`.

**Spec:** `docs/superpowers/specs/2026-06-04-turnkey-elegant-agent-sdk-design.md` (§4 API, §6.1 runtime, §6.5, §9 testing). This slice covers spec work units 2 and (the fakes-only part of) 6; units 1 (litellm Model bridge), 3 (MCP), 4 (approval), 5 (tools), 7 (A2A), 8 (expose-MCP) are later slices.

**Branch:** `feat/elegant-agent-sdk`. **Repo root:** `/home/developer/mcp/library`. Run all commands from `agent/` unless noted.

**Slice-1 scope note (read first):** Slice 1 deliberately uses pydantic-ai's native model providers, NOT litellm. `model="anthropic/claude-sonnet-4-6"` is normalized to pydantic-ai's `"anthropic:claude-sonnet-4-6"`. Restoring litellm (custom `Model`) is Slice 2.

---

## File structure (created in this slice)

- `agent/src/coactra/agent/sdk/__init__.py` — exports `Agent`, `Run`, `RunResult`, event DTOs, `AgentRuntimePort`, `PydanticAIRuntime`.
- `agent/src/coactra/agent/sdk/events.py` — event DTOs + `RunResult` (pure dataclasses).
- `agent/src/coactra/agent/sdk/models.py` — `resolve_model(model: str)` litellm-id → pydantic-ai model id/instance.
- `agent/src/coactra/agent/sdk/runtime.py` — `AgentRuntimePort` Protocol + `PydanticAIRuntime`.
- `agent/src/coactra/agent/sdk/facade.py` — `Agent` facade + `Run` handle.
- `agent/tests/sdk/test_events.py`, `test_models.py`, `test_runtime.py`, `test_runtime_stream.py`, `test_facade.py`.
- `agent/pyproject.toml` — add `agent` extra with `pydantic-ai-slim` (modify).
- `examples/elegant_agent.py` (repo root) — runnable offline demo.

---

## Task 0: Scaffold package + dependency

**Files:**
- Create: `agent/src/coactra/agent/sdk/__init__.py` (empty for now)
- Create: `agent/tests/sdk/__init__.py` (empty)
- Modify: `agent/pyproject.toml`

- [ ] **Step 1: Add the pydantic-ai extra**

In `agent/pyproject.toml`, under `[project.optional-dependencies]`, add:

```toml
agent = ["pydantic-ai-slim>=1.0"]
```

(If `[tool.uv.sources]` exists, no change needed — this is a real PyPI dep.) Then in the same file's `dev` extra, ensure it includes the agent extra deps so tests can import pydantic-ai, e.g. append `"pydantic-ai-slim>=1.0"` to the `dev` list.

- [ ] **Step 2: Install and verify import**

Run (from repo root): `python -m pip install -e './agent[dev]'`
Then run: `python -c "import pydantic_ai; from pydantic_ai.models.function import FunctionModel; from pydantic_ai.models.test import TestModel; print('ok')"`
Expected: prints `ok`. If the version pin fails, run `python -m pip install pydantic-ai-slim` and pin `agent/pyproject.toml` to the installed version (`python -c "import pydantic_ai, importlib.metadata as m; print(m.version('pydantic-ai-slim'))"`).

- [ ] **Step 3: Create empty package + test dirs**

Create `agent/src/coactra/agent/sdk/__init__.py` and `agent/tests/sdk/__init__.py` as empty files.

- [ ] **Step 4: Commit**

```bash
git add agent/pyproject.toml agent/src/coactra/agent/sdk/__init__.py agent/tests/sdk/__init__.py
git commit -m "feat(agent-sdk): scaffold sdk package + pydantic-ai dep"
```

---

## Task 1: Event DTOs + RunResult

**Files:**
- Create: `agent/src/coactra/agent/sdk/events.py`
- Test: `agent/tests/sdk/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/sdk/test_events.py
from coactra.agent.sdk.events import (
    Assistant, Thinking, ToolCall, ToolResult, Usage, Status, RunResult, Event,
)


def test_events_are_frozen_and_carry_identity():
    ev = Assistant(text="hi", run_id="r1", seq=3)
    assert ev.text == "hi" and ev.run_id == "r1" and ev.seq == 3
    import dataclasses
    try:
        ev.text = "no"  # frozen
        assert False, "expected FrozenInstanceError"
    except dataclasses.FrozenInstanceError:
        pass


def test_tool_call_and_result():
    call = ToolCall(id="t1", name="docs.search", args={"q": "x"}, run_id="r1", seq=1)
    ok = ToolResult(id="t1", name="docs.search", result={"hits": 2}, error=None, run_id="r1", seq=2)
    bad = ToolResult(id="t2", name="docs.search", result=None, error="boom", run_id="r1", seq=3)
    assert call.args["q"] == "x"
    assert ok.error is None and bad.error == "boom"


def test_run_result_factories():
    done = RunResult.finished(text="answer", output=None, usage=Usage(tokens=10, cost=0.0))
    failed = RunResult.failed("timeout")
    assert done.status == "finished" and done.text == "answer"
    assert failed.status == "error" and failed.error == "timeout"
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `agent/`): `python -m pytest tests/sdk/test_events.py -q`
Expected: FAIL — `ModuleNotFoundError: coactra.agent.sdk.events`.

- [ ] **Step 3: Write minimal implementation**

```python
# agent/src/coactra/agent/sdk/events.py
"""Public event DTOs and RunResult for the elegant Agent SDK.

Frozen, discriminated dataclasses. Every event carries run identity (run_id, seq)
so streams can be correlated, replayed, or traced.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Union


@dataclass(frozen=True, slots=True)
class _Base:
    run_id: str
    seq: int


@dataclass(frozen=True, slots=True)
class Assistant(_Base):
    text: str = ""


@dataclass(frozen=True, slots=True)
class Thinking(_Base):
    text: str = ""


@dataclass(frozen=True, slots=True)
class ToolCall(_Base):
    id: str = ""
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResult(_Base):
    id: str = ""
    name: str = ""
    result: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Usage(_Base):
    tokens: int = 0
    cost: float = 0.0


@dataclass(frozen=True, slots=True)
class Status(_Base):
    state: Literal["running", "finished", "error", "cancelled"] = "running"


Event = Union[Assistant, Thinking, ToolCall, ToolResult, Usage, Status]


@dataclass(frozen=True, slots=True)
class RunResult:
    status: Literal["finished", "error", "cancelled"]
    text: str = ""
    output: Any = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage | None = None
    messages: tuple[Any, ...] = ()
    error: str | None = None

    @classmethod
    def finished(cls, *, text: str = "", output: Any = None, usage: Usage | None = None,
                 tool_calls: tuple[ToolCall, ...] = (), messages: tuple[Any, ...] = ()) -> "RunResult":
        return cls(status="finished", text=text, output=output, usage=usage,
                   tool_calls=tool_calls, messages=messages)

    @classmethod
    def failed(cls, error: str) -> "RunResult":
        return cls(status="error", error=error)
```

Note: the test constructs `Usage(tokens=..., cost=...)` without `run_id/seq`; update the test's `Usage(...)` calls to include `run_id="r"`, `seq=0`, OR (preferred) give `_Base` fields defaults by declaring `run_id: str = ""` and `seq: int = 0` in `_Base`. Choose the defaults approach so `Usage` is usable both as an event and inside `RunResult`. Adjust `_Base` accordingly and re-run.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sdk/test_events.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/coactra/agent/sdk/events.py agent/tests/sdk/test_events.py
git commit -m "feat(agent-sdk): event DTOs + RunResult"
```

---

## Task 2: Model resolution (litellm id → pydantic-ai)

**Files:**
- Create: `agent/src/coactra/agent/sdk/models.py`
- Test: `agent/tests/sdk/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/sdk/test_models.py
import pytest
from coactra.agent.sdk.models import normalize_model_id


@pytest.mark.parametrize("given,expected", [
    ("anthropic/claude-sonnet-4-6", "anthropic:claude-sonnet-4-6"),
    ("openai/gpt-4o", "openai:gpt-4o"),
    ("anthropic:claude-sonnet-4-6", "anthropic:claude-sonnet-4-6"),  # already pydantic-ai form
    ("gpt-4o", "openai:gpt-4o"),  # bare → default to openai provider
])
def test_normalize_model_id(given, expected):
    assert normalize_model_id(given) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sdk/test_models.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# agent/src/coactra/agent/sdk/models.py
"""Map a litellm-style model id to a pydantic-ai model id (Slice 1).

litellm uses "provider/model"; pydantic-ai uses "provider:model". A bare id with
no provider defaults to the openai provider (pydantic-ai's own default convention).
Slice 2 replaces this with a litellm-backed custom Model so all providers route
through litellm with coactra-ai's thinking-model handling.
"""
from __future__ import annotations


def normalize_model_id(model: str) -> str:
    if ":" in model:
        return model
    if "/" in model:
        provider, _, name = model.partition("/")
        return f"{provider}:{name}"
    return f"openai:{model}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sdk/test_models.py -q`
Expected: PASS (4 cases).

- [ ] **Step 5: Commit**

```bash
git add agent/src/coactra/agent/sdk/models.py agent/tests/sdk/test_models.py
git commit -m "feat(agent-sdk): litellm-style model id normalization"
```

---

## Task 3: AgentRuntimePort + PydanticAIRuntime.run (non-streaming)

**Files:**
- Create: `agent/src/coactra/agent/sdk/runtime.py`
- Test: `agent/tests/sdk/test_runtime.py`

**Reference (verified from pydantic-ai docs):**
- `from pydantic_ai import Agent` ; `agent = Agent(model, instructions=..., output_type=...)`
- `result = await agent.run(prompt, message_history=...)` → result has `.output`, `.all_messages()`, `.new_messages()`, `.usage()`
- Offline: `from pydantic_ai.models.function import FunctionModel, AgentInfo` ; `from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart` ; `agent.override(model=FunctionModel(fn))`

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/sdk/test_runtime.py
import pytest
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from coactra.agent.sdk.runtime import PydanticAIRuntime


def _final_text(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("the first check is replication lag")])


@pytest.mark.anyio
async def test_runtime_run_returns_text():
    rt = PydanticAIRuntime(model=FunctionModel(_final_text), instructions="be terse")
    result = await rt.run("triage db latency", run_id="r1")
    assert result.status == "finished"
    assert "replication lag" in result.text


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sdk/test_runtime.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# agent/src/coactra/agent/sdk/runtime.py
"""AgentRuntimePort + the default pydantic-ai runtime (Slice 1: run only)."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic_ai import Agent as PydAgent

from coactra.agent.sdk.events import RunResult, Usage
from coactra.agent.sdk.models import normalize_model_id


@runtime_checkable
class AgentRuntimePort(Protocol):
    async def run(self, prompt: str, *, run_id: str, output_type: type | None = None,
                  message_history: list[Any] | None = None) -> RunResult: ...


class PydanticAIRuntime:
    """Default runtime. `model` is a str (litellm-style id) or a pydantic-ai model instance
    (e.g. FunctionModel/TestModel in tests)."""

    def __init__(self, *, model: Any, instructions: str | None = None,
                 tools: list[Any] | None = None) -> None:
        self._model = normalize_model_id(model) if isinstance(model, str) else model
        self._instructions = instructions
        self._tools = tools or []

    def _build(self, output_type: type | None) -> PydAgent:
        kwargs: dict[str, Any] = {"instructions": self._instructions, "tools": self._tools}
        if output_type is not None:
            kwargs["output_type"] = output_type
        return PydAgent(self._model, **kwargs)

    async def run(self, prompt: str, *, run_id: str, output_type: type | None = None,
                  message_history: list[Any] | None = None) -> RunResult:
        agent = self._build(output_type)
        result = await agent.run(prompt, message_history=message_history)
        output = result.output
        text = output if isinstance(output, str) else ""
        usage = None
        try:
            u = result.usage()
            usage = Usage(run_id=run_id, seq=0, tokens=getattr(u, "total_tokens", 0) or 0)
        except Exception:
            usage = None
        return RunResult.finished(
            text=text,
            output=None if isinstance(output, str) else output,
            usage=usage,
            messages=tuple(result.all_messages()),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sdk/test_runtime.py -q`
Expected: PASS. If `result.usage()` or `all_messages()` names differ in the installed version, adjust to the installed API (run `python -c "import pydantic_ai, inspect; ..."` or read the installed `pydantic_ai` result type) — the test only asserts text, so usage/messages mapping can be corrected without breaking it.

- [ ] **Step 5: Commit**

```bash
git add agent/src/coactra/agent/sdk/runtime.py agent/tests/sdk/test_runtime.py
git commit -m "feat(agent-sdk): AgentRuntimePort + PydanticAIRuntime.run"
```

---

## Task 4: Structured output via output_type

**Files:**
- Modify: `agent/tests/sdk/test_runtime.py` (add a test)

- [ ] **Step 1: Write the failing test**

```python
# append to agent/tests/sdk/test_runtime.py
from pydantic import BaseModel
from pydantic_ai.models.test import TestModel


class TriagePlan(BaseModel):
    steps: list[str]


@pytest.mark.anyio
async def test_runtime_structured_output():
    rt = PydanticAIRuntime(model=TestModel())  # TestModel fabricates schema-valid data
    result = await rt.run("plan", run_id="r2", output_type=TriagePlan)
    assert result.status == "finished"
    assert isinstance(result.output, TriagePlan)
    assert isinstance(result.output.steps, list)
```

- [ ] **Step 2: Run to verify it fails (or passes)**

Run: `python -m pytest tests/sdk/test_runtime.py::test_runtime_structured_output -q`
Expected: PASS if Task 3's `run` already threads `output_type`. If it fails because `output` is being coerced to `""`, fix `run` so non-str output is returned in `RunResult.output` (it already does). If `TestModel` cannot build the schema, replace with a `FunctionModel` that returns a `ToolCallPart` for the final-output tool — see pydantic-ai testing docs.

- [ ] **Step 3: Commit**

```bash
git add agent/tests/sdk/test_runtime.py
git commit -m "test(agent-sdk): structured output via output_type"
```

---

## Task 5: PydanticAIRuntime.stream → coactra events

**Files:**
- Modify: `agent/src/coactra/agent/sdk/runtime.py` (add `stream`)
- Test: `agent/tests/sdk/test_runtime_stream.py`

**Reference:** pydantic-ai exposes streaming via `agent.iter(prompt)` (async-context, iterate graph nodes) and an event stream. Implement `stream` over the installed pydantic-ai streaming API and MAP to coactra events. The test below pins the OBSERVABLE coactra-event contract (a tool call surfaces a `ToolCall` then `ToolResult`, ending with an `Assistant` and a terminal `Status("finished")`), independent of pydantic-ai's internal event names.

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/sdk/test_runtime_stream.py
import pytest
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from coactra.agent.sdk.runtime import PydanticAIRuntime
from coactra.agent.sdk.events import Assistant, ToolCall, ToolResult, Status


def _echo_tool(value: str) -> str:
    """Return the value unchanged."""
    return f"checked:{value}"


def _two_step(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    # 1st model call → ask to run the tool; 2nd → final text
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart("_echo_tool", {"value": "replication"})])
    return ModelResponse(parts=[TextPart("done: replication checked")])


@pytest.mark.anyio
async def test_stream_emits_tool_then_assistant():
    rt = PydanticAIRuntime(model=FunctionModel(_two_step), tools=[_echo_tool])
    kinds = []
    async for ev in rt.stream("check replication", run_id="r3"):
        kinds.append(type(ev).__name__)
    assert "ToolCall" in kinds
    assert "ToolResult" in kinds
    assert kinds[-1] == "Status"  # terminal


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sdk/test_runtime_stream.py -q`
Expected: FAIL — `PydanticAIRuntime` has no `stream`.

- [ ] **Step 3: Implement `stream`**

Add an async generator `stream(self, prompt, *, run_id, output_type=None, message_history=None)` to `PydanticAIRuntime`. Use the installed pydantic-ai streaming API — `agent.iter(...)` is the documented manual-iteration entry point. For each node, emit coactra events with an incrementing `seq`:
- model text part → `Assistant(text=..., run_id=run_id, seq=seq)`
- a tool-call request → `ToolCall(id=part.tool_call_id, name=part.tool_name, args=part.args_as_dict(), run_id=run_id, seq=seq)`
- a tool return → `ToolResult(id=..., name=..., result=..., error=None, run_id=run_id, seq=seq)`
- finally `yield Status(state="finished", run_id=run_id, seq=seq)`

Consult the installed pydantic-ai's `agent.iter()` / node and message-part types (`from pydantic_ai.messages import ...`) for exact attribute names; the test asserts only the coactra event sequence, so internal mapping can be adjusted to the installed version without changing the contract. Wrap the body in try/except and emit `Status(state="error")` as the terminal event on failure.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sdk/test_runtime_stream.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/src/coactra/agent/sdk/runtime.py agent/tests/sdk/test_runtime_stream.py
git commit -m "feat(agent-sdk): streaming runtime → coactra events"
```

---

## Task 6: The `Agent` facade + `Run` handle

**Files:**
- Create: `agent/src/coactra/agent/sdk/facade.py`
- Modify: `agent/src/coactra/agent/sdk/__init__.py`
- Test: `agent/tests/sdk/test_facade.py`

- [ ] **Step 1: Write the failing test**

```python
# agent/tests/sdk/test_facade.py
import pytest
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic import BaseModel
from pydantic_ai.models.test import TestModel
from coactra.agent.sdk import Agent


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello from the agent")])


class Plan(BaseModel):
    steps: list[str]


@pytest.mark.anyio
async def test_create_send_wait():
    agent = await Agent.create(model=FunctionModel(_final), instructions="be brief")
    run = await agent.send("hi")
    result = await run.wait()
    assert "hello from the agent" in result.text
    await agent.aclose()


@pytest.mark.anyio
async def test_run_structured():
    agent = await Agent.create(model=TestModel())
    plan = await agent.run("make a plan", output_type=Plan)
    assert isinstance(plan, Plan)
    await agent.aclose()


@pytest.mark.anyio
async def test_async_context_manager():
    async with await Agent.create(model=FunctionModel(_final)) as agent:
        run = await agent.send("hi")
        async for _ev in run.stream():
            pass
        assert (await run.wait()).status == "finished"


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/sdk/test_facade.py -q`
Expected: FAIL — `coactra.agent.sdk` has no `Agent`.

- [ ] **Step 3: Implement the facade**

```python
# agent/src/coactra/agent/sdk/facade.py
"""The elegant async Agent facade (Slice 1: model + run/stream/structured)."""
from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from coactra.agent.sdk.events import Event, RunResult
from coactra.agent.sdk.runtime import AgentRuntimePort, PydanticAIRuntime


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
        events: list[Event] = []
        async for ev in self._runtime.stream(
            self._prompt, run_id=self.id, output_type=self._output_type,
            message_history=self._history,
        ):
            events.append(ev)
            yield ev
        # derive a result from the streamed events if wait() wasn't used
        if self._result is None:
            text = "".join(getattr(e, "text", "") for e in events if type(e).__name__ == "Assistant")
            self._result = RunResult.finished(text=text)

    async def wait(self) -> RunResult:
        if self._result is None:
            self._result = await self._runtime.run(
                self._prompt, run_id=self.id, output_type=self._output_type,
                message_history=self._history,
            )
        return self._result


class Agent:
    """Elegant async agent facade. Slice 1 wires the model + runtime only."""

    def __init__(self, runtime: AgentRuntimePort) -> None:
        self._runtime = runtime

    @classmethod
    async def create(cls, *, model: Any, instructions: str | None = None,
                     tools: list[Any] | None = None,
                     runtime: AgentRuntimePort | None = None) -> "Agent":
        rt = runtime or PydanticAIRuntime(model=model, instructions=instructions, tools=tools)
        return cls(rt)

    async def send(self, message: str, *, output_type: type | None = None,
                   message_history: list[Any] | None = None) -> Run:
        return Run(self._runtime, message, run_id=f"run-{uuid.uuid4().hex[:12]}",
                   output_type=output_type, message_history=message_history)

    async def run(self, message: str, *, output_type: type | None = None,
                  message_history: list[Any] | None = None) -> Any:
        result = await (await self.send(message, output_type=output_type,
                                        message_history=message_history)).wait()
        return result.output if output_type is not None else result.text

    async def aclose(self) -> None:
        # Slice 1 has no network resources to close; later slices close MCP/A2A clients here.
        return None

    async def __aenter__(self) -> "Agent":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
```

Then set `agent/src/coactra/agent/sdk/__init__.py`:

```python
from coactra.agent.sdk.events import (
    Assistant, Event, RunResult, Status, Thinking, ToolCall, ToolResult, Usage,
)
from coactra.agent.sdk.facade import Agent, Run
from coactra.agent.sdk.runtime import AgentRuntimePort, PydanticAIRuntime

__all__ = [
    "Agent", "Run", "RunResult", "Event",
    "Assistant", "Thinking", "ToolCall", "ToolResult", "Usage", "Status",
    "AgentRuntimePort", "PydanticAIRuntime",
]
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/sdk/ -q`
Expected: PASS (all sdk tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/coactra/agent/sdk/facade.py agent/src/coactra/agent/sdk/__init__.py agent/tests/sdk/test_facade.py
git commit -m "feat(agent-sdk): Agent facade (create/send/run/stream) + Run handle"
```

---

## Task 7: Runnable offline example + agent-package export

**Files:**
- Create: `examples/elegant_agent.py`
- Modify: `agent/src/coactra/agent/__init__.py` (export `Agent` as `SdkAgent` to avoid clobbering the existing `Agent`)

- [ ] **Step 1: Export without clobbering the existing Agent**

The existing `coactra.agent.Agent` (low-level) must NOT be shadowed. In `agent/src/coactra/agent/__init__.py`, add:

```python
from coactra.agent.sdk import Agent as SdkAgent  # elegant facade; umbrella `from coactra import Agent` lands in a later slice
```

(Do not rebind the existing `Agent` name. The umbrella `from coactra import Agent` re-export is deferred to the finalization slice per the spec.)

- [ ] **Step 2: Write the example (offline, no API key)**

```python
# examples/elegant_agent.py
"""Runnable offline demo of the elegant Agent SDK (Slice 1).

Uses pydantic-ai's FunctionModel so it runs with no API key or network.
With a real model id (e.g. "anthropic/claude-sonnet-4-6") and ANTHROPIC_API_KEY,
swap `model=` for the string to call a real model.
"""
import asyncio

from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelResponse, TextPart

from coactra.agent.sdk import Agent


def _model(messages, info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("first check: replication lag; second: slow queries")])


async def main() -> None:
    agent = await Agent.create(model=FunctionModel(_model), instructions="SRE triage, be terse")
    run = await agent.send("triage db latency")
    async for ev in run.stream():
        print(type(ev).__name__, getattr(ev, "text", ""))
    print("FINAL:", (await run.wait()).text)
    await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run the example**

Run (from repo root): `python examples/elegant_agent.py`
Expected: prints streamed event type names and `FINAL: first check: replication lag; ...`.

- [ ] **Step 4: Run the full sdk suite once more**

Run (from `agent/`): `python -m pytest tests/sdk/ -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/elegant_agent.py agent/src/coactra/agent/__init__.py
git commit -m "feat(agent-sdk): offline example + SdkAgent export"
```

---

## Done-criteria for Slice 1

- `python -m pytest agent/tests/sdk/ -q` passes (events, models, runtime, structured, stream, facade).
- `python examples/elegant_agent.py` runs offline and prints a final answer.
- `from coactra.agent.sdk import Agent` works; `Agent.create/send/run/stream/aclose` + `async with` behave per tests.
- No change to existing `make_agent` / `coactra.agent.Agent` behavior (run `python -m pytest agent/tests -q` — the pre-existing suite still passes).

## Next slices (separate plans)

- Slice 2: litellm-backed custom pydantic-ai `Model` (restore "everything via litellm" + thinking-model handling) — spec unit 1.
- Slice 3: MCP client (`MCPClientPort`, http+stdio) + `[mcp]` extra — spec unit 3.
- Slice 4: approval gate — spec unit 4.
- Slice 5: capability→tool bridge + declarative config (memory/workspace/org/work) + `enabled_tools()` — spec units 5, 6.
- Slice 6: A2A inbound (required verifier) + outbound peers + `call_agent` — spec unit 7.
- Slice 7: expose-as-MCP + umbrella `from coactra import Agent` — spec unit 8.
