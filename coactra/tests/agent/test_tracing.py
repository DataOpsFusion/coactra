from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Policy, Scope, Team
from coactra.agent.workflow import Workflow, step
from coactra.model import ModelProfile, ModelResolver, ModelRoute


class RecordingSpan:
    def __init__(self, name: str, attributes: dict | None) -> None:
        self.name = name
        self.attributes = attributes or {}
        self.events = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        self.events.append((name, attributes or {}))


class RecordingTracer:
    def __init__(self) -> None:
        self.spans = []

    def start_as_current_span(self, name: str, attributes: dict | None = None):
        span = RecordingSpan(name, attributes)
        self.spans.append(span)
        return span


def _echo_model() -> FunctionModel:
    def _reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("model ok")])

    return FunctionModel(_reply)


async def _make_agent(*, tracer):
    team = Team(
        scope=Scope(tenant_id="acme", namespace="trace"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="default", profile=ModelProfile(name="default", model=_echo_model())
                )
            ]
        ),
    )
    return await team.add_agent(
        name="sre-agent",
        tracer=tracer,
    )


async def test_agent_run_emits_model_trace_span():
    tracer = RecordingTracer()
    agent = await _make_agent(tracer=tracer)

    assert await agent.run("hello") == "model ok"

    span = tracer.spans[0]
    assert span.name == "coactra.agent.run"
    assert span.attributes["coactra.agent.name"] == "sre-agent"
    assert span.attributes["coactra.tenant_id"] == "acme"
    assert [event[0] for event in span.events] == [
        "coactra.model.request",
        "coactra.model.response",
    ]


async def test_agent_stream_emits_model_trace_span():
    tracer = RecordingTracer()
    agent = await _make_agent(tracer=tracer)

    run = await agent.send("hello")
    async for _event in run.stream():
        pass

    span = tracer.spans[0]
    assert span.name == "coactra.agent.stream"
    assert span.attributes["coactra.agent.name"] == "sre-agent"
    assert [event[0] for event in span.events] == [
        "coactra.model.request",
        "coactra.model.response",
    ]


class TracedAgent:
    _name = "worker"

    async def run(self, instruction: str) -> str:
        return f"done:{instruction}"


class TracedTeam:
    def member(self, name: str):
        return TracedAgent() if name == "worker" else None

    def match_skill(self, skill_id: str):
        return TracedAgent()


async def test_workflow_run_emits_workflow_and_step_trace_events():
    tracer = RecordingTracer()
    wf = Workflow("trace-workflow", steps=[step("inspect", agent="worker")])

    run = await wf.run(TracedTeam(), run_id="wf-1", tracer=tracer)

    assert run.status == "completed"
    span = tracer.spans[0]
    assert span.name == "coactra.workflow.run"
    assert span.attributes["coactra.workflow.name"] == "trace-workflow"
    assert span.attributes["coactra.run_id"] == "wf-1"
    assert [event[0] for event in span.events] == [
        "coactra.workflow.step.start",
        "coactra.workflow.step.complete",
        "coactra.workflow.complete",
    ]


class RecordingEngine:
    async def start(self, procedure, state, ctx, *, thread_id=None):
        class Run:
            status = "completed"
            thread_id = "engine-run"
            state = {"step_0_result": "engine done"}

        return Run()


async def test_workflow_engine_run_emits_trace_span():
    tracer = RecordingTracer()
    wf = Workflow("engine-workflow", steps=[step("inspect", agent="worker")])

    run = await wf.run(TracedTeam(), run_id="wf-engine", engine=RecordingEngine(), tracer=tracer)

    assert run.status == "completed"
    span = tracer.spans[0]
    assert span.name == "coactra.workflow.run"
    assert span.attributes["coactra.workflow.name"] == "engine-workflow"
    assert [event[0] for event in span.events] == [
        "coactra.workflow.engine.start",
        "coactra.workflow.engine.complete",
    ]
