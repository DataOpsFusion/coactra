from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra.agent import Agent
from coactra.workflow import Procedure, ProcedureVersion, Scope, Step


def _echo_model() -> FunctionModel:
    def _reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(_reply)


class RecordingWorkflowEngine:
    def __init__(self) -> None:
        self.calls = []

    async def start(self, procedure, state, ctx, *, thread_id=None):
        self.calls.append({
            "procedure": procedure,
            "state": state,
            "scope": ctx.scope,
            "thread_id": thread_id,
        })

        class Run:
            status = "completed"
            state = {"ok": True, "procedure": procedure.name}
            result = None

        return Run()


def _procedure() -> Procedure:
    return Procedure(
        name="Deploy Service",
        steps=[Step(id="deploy", kind="task")],
        is_induced=True,
    )


async def test_agent_create_learned_procedure_publishes_skill_and_replay_tool():
    engine = RecordingWorkflowEngine()

    agent = await Agent.create(
        model=_echo_model(),
        name="sre-agent",
        tenant="acme",
        learned=[_procedure()],
        procedure_engine=engine,
        allow_unreviewed_learned=True,
    )

    card = agent.card
    assert card is not None
    assert {skill["id"] for skill in card["skills"]} == {"procedure.deploy_service"}

    replay = next(t for t in agent._tools if t.__name__ == "replay_deploy_service")
    output = await replay({"service": "api"})

    assert "Deploy Service" in output
    assert engine.calls[0]["procedure"].name == "Deploy Service"
    assert engine.calls[0]["state"] == {"service": "api"}
    assert engine.calls[0]["scope"] == Scope(tenant_id="acme")


async def test_agent_create_learned_accepts_promoted_procedure_version():
    version = ProcedureVersion(
        procedure=_procedure(),
        version=2,
        promoted_by="human:senior",
    )

    agent = await Agent.create(
        model=_echo_model(),
        name="sre-agent",
        tenant="acme",
        learned=version,
        procedure_engine=RecordingWorkflowEngine(),
    )

    assert agent.card["skills"][0]["id"] == "procedure.deploy_service"
    assert any(t.__name__ == "replay_deploy_service" for t in agent._tools)


async def test_agent_create_learned_rejects_unreviewed_procedure_by_default():
    try:
        await Agent.create(
            model=_echo_model(),
            name="sre-agent",
            tenant="acme",
            learned=[_procedure()],
            procedure_engine=RecordingWorkflowEngine(),
        )
    except ValueError as exc:
        assert "promoted" in str(exc).lower()
    else:
        raise AssertionError("unreviewed learned procedure was accepted")
