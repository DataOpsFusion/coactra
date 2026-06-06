from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra.agent import Agent
from coactra.agent.workflow import Workflow, step


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


async def test_agent_run_emits_model_trace_span():
    tracer = RecordingTracer()
    agent = await Agent.create(
        model=_echo_model(),
        name="sre-agent",
        tenant="acme",
        tracer=tracer,
    )

    assert await agent.run("hello") == "model ok"

    span = tracer.spans[0]
    assert span.name == "coactra.agent.run"
    assert span.attributes["coactra.agent.name"] == "sre-agent"
    assert span.attributes["coactra.tenant_id"] == "acme"
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

    def match(self, needs: str):
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
