"""TDD tests for Workflow.run_goal (triage) and durable checkpointing."""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope
from coactra.agent.checkpoint import InMemoryCheckpointStore, run_from_state
from coactra.agent.planner import PlannedPlan, PlannedStep
from coactra.agent.playbook_store import InMemoryPlaybookStore
from coactra.agent.skills import Skill
from coactra.agent.workflow import Workflow
from coactra.team import Team
from coactra.workflow.playbook import Playbook, ProofBundle, VerificationReceipt, step


def _proof_bundle() -> ProofBundle:
    return ProofBundle(
        summary="verified",
        receipts=(
            VerificationReceipt(
                command="pytest -q",
                exit_code=0,
                stdout_sha256="stdout",
                stderr_sha256="stderr",
            ),
        ),
    )


def _make_echo_model(label: str):
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        last_text = ""
        for msg in reversed(messages):
            for part in msg.parts:
                if hasattr(part, "content") and isinstance(part.content, str):
                    last_text = part.content
                    break
            if last_text:
                break
        return ModelResponse(parts=[TextPart(f"{label}: {last_text}")])

    return FunctionModel(_fn)


class _RaisingClient:
    def structured(self, schema, prompt, **kwargs):
        raise AssertionError("plan_playbook should NOT have been called (store hit expected)")


class _FakeClient:
    def __init__(self, plan: PlannedPlan) -> None:
        self._plan = plan

    def structured(self, schema, prompt, **kwargs):
        return self._plan


@pytest.fixture
async def team():
    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="cert",
                    profile=ModelProfile(name="cert", model=_make_echo_model("cert-agent")),
                ),
                ModelRoute(
                    capability="deploy",
                    profile=ModelProfile(name="deploy", model=_make_echo_model("deploy-agent")),
                ),
            ]
        ),
    )
    await team.add_agent(
        name="cert-agent",
        model_capability="cert",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
        expose=True,
    )
    await team.add_agent(
        name="deploy-agent",
        model_capability="deploy",
        skills=[Skill("infra.deploy", description="deploy services")],
        expose=True,
    )
    return team


async def test_run_goal_store_hit_uses_promoted_playbook(team):
    store = InMemoryPlaybookStore()
    pb = Playbook(name="rotate cert", steps=[step("rotate the cert", requires_skill="cert.rotate")])
    store.save_candidate(pb)
    store.promote("rotate cert")

    run = await Workflow.run_goal("rotate cert", team, store=store, client=_RaisingClient())

    assert run.status == "completed"
    assert len(run.results) == 1
    assert run.results[0].agent == "cert-agent"


async def test_run_goal_store_hit_returns_workflow_run(team):
    from coactra.workflow.playbook import WorkflowRun

    store = InMemoryPlaybookStore()
    pb = Playbook(
        name="deploy service",
        steps=[step("deploy the service", requires_skill="infra.deploy")],
    )
    store.save_candidate(pb)
    store.promote("deploy service")

    run = await Workflow.run_goal("deploy service", team, store=store, client=_RaisingClient())

    assert isinstance(run, WorkflowRun)


async def test_run_goal_miss_calls_planner_and_saves_candidate(team):
    store = InMemoryPlaybookStore()
    goal = "rotate cert and redeploy"

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", requires_skill="infra.deploy"),
        ]
    )
    fake_client = _FakeClient(fixed_plan)

    run = await Workflow.run_goal(goal, team, store=store, client=fake_client)

    assert run.status == "completed"
    pb = store.get(goal)
    assert pb is not None
    assert pb.name == goal
    assert store.find(goal) is None


async def test_run_goal_miss_no_store_still_runs(team):
    goal = "rotate cert"
    fixed_plan = PlannedPlan(
        steps=[PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate")]
    )
    fake_client = _FakeClient(fixed_plan)

    run = await Workflow.run_goal(goal, team, store=None, client=fake_client)

    assert run.status == "completed"
    assert len(run.results) == 1


async def test_run_goal_without_client_derives_planner_client_from_team_model_config(monkeypatch):
    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="cert",
                    profile=ModelProfile(
                        name="cert",
                        model="openai/qwen3.6-plus",
                        api_base="https://opencode.ai/zen/go/v1",
                        api_key="oc-test-key",
                    ),
                ),
                ModelRoute(
                    capability="deploy",
                    profile=ModelProfile(
                        name="deploy",
                        model="openai/qwen3.6-plus",
                        api_base="https://opencode.ai/zen/go/v1",
                        api_key="oc-test-key",
                    ),
                ),
            ]
        ),
    )
    cert = await team.add_agent(
        name="cert-agent",
        model_capability="cert",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
        expose=True,
    )
    deploy = await team.add_agent(
        name="deploy-agent",
        model_capability="deploy",
        skills=[Skill("infra.deploy", description="deploy services")],
        expose=True,
    )

    async def _fake_run(message: str, **kwargs) -> str:
        return f"ran: {message}"

    cert.run = _fake_run
    deploy.run = _fake_run

    captured: list[dict] = []

    class CapturingClient:
        def __init__(self, **kwargs) -> None:
            captured.append(kwargs)

        def structured(self, schema, prompt, **kwargs):
            return PlannedPlan(
                steps=[
                    PlannedStep(
                        instruction="Rotate the TLS certificate",
                        requires_skill="cert.rotate",
                    ),
                    PlannedStep(instruction="Redeploy the service", requires_skill="infra.deploy"),
                ]
            )

    monkeypatch.setattr("coactra.ai.Client", CapturingClient)

    run = await Workflow.run_goal("rotate cert and redeploy", team)

    assert run.status == "completed"
    assert captured == [
        {
            "model": "openai/qwen3.6-plus",
            "api_base": "https://opencode.ai/zen/go/v1",
            "api_key": "oc-test-key",
        }
    ]


async def test_run_goal_failed_run_does_not_save_candidate(team):
    store = InMemoryPlaybookStore()
    goal = "do quantum stuff"

    fixed_plan = PlannedPlan(
        steps=[PlannedStep(instruction="Entangle qubits", requires_skill="quantum.entanglement")]
    )
    fake_client = _FakeClient(fixed_plan)

    run = await Workflow.run_goal(goal, team, store=store, client=fake_client)

    assert run.status == "failed"
    assert store.get(goal) is None


async def test_checkpoint_saved_after_each_step(team):
    cp_store = InMemoryCheckpointStore()
    run_id = "chk-test-1"

    wf = Workflow(
        "two-step",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("deploy the service", requires_skill="infra.deploy"),
        ],
    )
    run = await wf.run(team, checkpoint=cp_store, run_id=run_id)

    assert run.status == "completed"
    state = cp_store.load(run_id)
    assert state is not None

    reconstructed = run_from_state(state)
    assert len(reconstructed.results) == 2
    assert all(r.status == "done" for r in reconstructed.results)


async def test_checkpoint_saved_at_interrupt(team):
    cp_store = InMemoryCheckpointStore()
    run_id = "chk-test-interrupt"

    wf = Workflow(
        "approval-wf",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("deploy the service", requires_skill="infra.deploy", approve=True),
        ],
    )
    interrupted = await wf.run(team, checkpoint=cp_store, run_id=run_id)

    assert interrupted.status == "interrupted"
    state = cp_store.load(run_id)
    assert state is not None

    reconstructed = run_from_state(state)
    assert len(reconstructed.results) == 1
    assert reconstructed.results[0].status == "done"
    assert reconstructed.status == "interrupted"
    assert reconstructed.pending_index == 1


async def test_no_checkpoint_store_run_still_works(team):
    wf = Workflow("plain", steps=[step("rotate the cert", requires_skill="cert.rotate")])
    run = await wf.run(team)
    assert run.status == "completed"


async def test_resume_from_interrupted_approval_completes(team):
    cp_store = InMemoryCheckpointStore()
    run_id = "resume-test-1"

    wf = Workflow(
        "approval-wf",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("deploy the service", requires_skill="infra.deploy", approve=True),
        ],
    )

    interrupted = await wf.run(team, checkpoint=cp_store, run_id=run_id)
    assert interrupted.status == "interrupted"

    final = await wf.resume_from(
        cp_store,
        run_id,
        team,
        decision=True,
        proof_bundle=_proof_bundle(),
    )

    assert final.status == "completed"
    assert len(final.results) == 2
    assert final.results[0].agent == "cert-agent"
    assert final.results[1].agent == "deploy-agent"
    assert final.results[1].status == "done"
    assert len(final.approvals) == 1
    assert final.approvals[0].decision is True


async def test_resume_from_interrupted_approval_denied(team):
    cp_store = InMemoryCheckpointStore()
    run_id = "resume-denied"

    wf = Workflow(
        "approval-wf",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("deploy the service", requires_skill="infra.deploy", approve=True),
        ],
    )

    interrupted = await wf.run(team, checkpoint=cp_store, run_id=run_id)
    assert interrupted.status == "interrupted"

    denied = await wf.resume_from(cp_store, run_id, team, decision=False)

    assert denied.status == "denied"
    assert len(denied.results) == 2
    assert denied.results[1].status == "skipped"
    assert denied.approvals[0].decision is False

    saved = run_from_state(cp_store.load(run_id))
    assert saved.status == "denied"
    assert len(saved.results) == 2
    assert saved.results[1].status == "skipped"


async def test_resume_from_non_approval_run_continues(team):
    cp_store = InMemoryCheckpointStore()
    run_id = "resume-mid"

    from coactra.agent.checkpoint import run_to_state
    from coactra.workflow.playbook import StepResult, WorkflowRun

    mid_run = WorkflowRun(
        name="two-step",
        status="running",
        results=[
            StepResult(
                instruction="rotate the cert",
                agent="cert-agent",
                output="done",
                status="done",
            )
        ],
        pending_index=None,
        approvals=[],
    )
    cp_store.save(run_id, run_to_state(mid_run))

    wf = Workflow(
        "two-step",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("deploy the service", requires_skill="infra.deploy"),
        ],
    )

    final = await wf.resume_from(cp_store, run_id, team)
    assert final.status == "completed"
    assert len(final.results) == 2
    assert final.results[0].status == "done"
    assert final.results[1].status == "done"


async def test_resume_from_missing_checkpoint_raises(team):
    cp_store = InMemoryCheckpointStore()

    wf = Workflow("any", steps=[step("do it", requires_skill="cert.rotate")])

    with pytest.raises((ValueError, KeyError)):
        await wf.resume_from(cp_store, "nonexistent-run-id", team)


class _BridgeAgent:
    def __init__(self, name: str, tenant: str = "acme") -> None:
        self._name = name
        self._tenant = tenant

    async def run(self, instruction: str) -> str:
        return f"{self._name}: {instruction}"


class _BridgeTeam:
    def __init__(self) -> None:
        self._members = {
            "alpha-agent": _BridgeAgent("alpha-agent"),
            "beta-agent": _BridgeAgent("beta-agent"),
        }

    def member(self, name: str):
        return self._members.get(name)

    def match_skill(self, skill_id: str):
        return self._members.get("alpha-agent")


async def test_public_workflow_runs_and_resumes_with_durable_langgraph_engine():
    pytest.importorskip("langgraph")
    from langgraph.checkpoint.memory import MemorySaver

    from coactra.workflow import DurableLangGraphEngine

    engine = DurableLangGraphEngine(checkpointer=MemorySaver())
    team = _BridgeTeam()
    wf = Workflow(
        "public-durable",
        steps=[
            step("collect evidence", agent="alpha-agent"),
            step("apply change", agent="beta-agent", approve=True),
        ],
    )

    paused = await wf.run(team, engine=engine, run_id="durable-bridge")

    assert paused.status == "interrupted"
    assert paused.pending_index == 1
    assert paused.thread_id == "acme:durable-bridge"
    assert [r.agent for r in paused.results] == ["alpha-agent"]

    final = await wf.resume_engine(engine, paused.thread_id, team, decision=True)

    assert final.status == "completed"
    assert [r.agent for r in final.results] == ["alpha-agent", "beta-agent"]
    assert [r.status for r in final.results] == ["done", "done"]
