"""TDD tests for Workflow.run_goal (triage) and durable checkpointing.

RED phase: written before implementation exists.

Covers:
1. run_goal — store hit: find(goal) returns a promoted playbook; run_goal uses it.
   No planning happens (fake client raises if called).
2. run_goal — miss → plan → candidate: empty store + fake client; after run_goal
   the playbook is a CANDIDATE (get returns it, find still returns None).
3. checkpoint after each step: run(team, checkpoint=store, run_id="r1") saves state
   after each completed step with status="running", and saves at interrupt too.
4. resume_from: interrupted checkpoint + resume_from(store, run_id, team, decision=True)
   reconstructs from store and completes the run.
"""
from __future__ import annotations

import pytest
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart

from coactra.agent import Agent
from coactra.agent.checkpoint import InMemoryCheckpointStore, run_from_state
from coactra.agent.playbook_store import InMemoryPlaybookStore
from coactra.agent.planner import PlannedPlan, PlannedStep
from coactra.agent.skills import Skill
from coactra.agent.team import Team
from coactra.agent.workflow import Playbook, Workflow, step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_echo_model(label: str):
    """Return a FunctionModel that echoes '<label>: <prompt>'."""
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
    """A fake LLM client that raises if called — used to assert no planning happens."""
    def structured(self, schema, prompt, **kwargs):
        raise AssertionError("plan_playbook should NOT have been called (store hit expected)")


class _FakeClient:
    """A fake LLM client returning a fixed PlannedPlan."""
    def __init__(self, plan: PlannedPlan) -> None:
        self._plan = plan

    def structured(self, schema, prompt, **kwargs):
        return self._plan


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def cert_agent():
    return await Agent.create(
        model=_make_echo_model("cert-agent"),
        name="cert-agent",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
    )


@pytest.fixture
async def deploy_agent():
    return await Agent.create(
        model=_make_echo_model("deploy-agent"),
        name="deploy-agent",
        skills=[Skill("infra.deploy", description="deploy services")],
    )


@pytest.fixture
def team(cert_agent, deploy_agent):
    return Team([cert_agent, deploy_agent])


# ---------------------------------------------------------------------------
# 1. run_goal — store hit uses the promoted playbook, no planning
# ---------------------------------------------------------------------------

async def test_run_goal_store_hit_uses_promoted_playbook(team):
    """If store.find(goal) returns a playbook, run_goal runs it without planning."""
    store = InMemoryPlaybookStore()

    # Pre-build and promote a playbook
    pb = Playbook(name="rotate cert", steps=[
        step("rotate the cert", needs="cert rotation"),
    ])
    store.save_candidate(pb)
    store.promote("rotate cert")

    # The raising client must never be called
    run = await Workflow.run_goal(
        "rotate cert",
        team,
        store=store,
        client=_RaisingClient(),
    )

    assert run.status == "completed"
    assert len(run.results) == 1
    assert run.results[0].agent == "cert-agent"


async def test_run_goal_store_hit_returns_workflow_run(team):
    """run_goal returns a WorkflowRun when a playbook is found in the store."""
    from coactra.agent.workflow import WorkflowRun

    store = InMemoryPlaybookStore()
    pb = Playbook(name="deploy service", steps=[
        step("deploy the service", needs="infra.deploy"),
    ])
    store.save_candidate(pb)
    store.promote("deploy service")

    run = await Workflow.run_goal(
        "deploy service",
        team,
        store=store,
        client=_RaisingClient(),
    )

    assert isinstance(run, WorkflowRun)


# ---------------------------------------------------------------------------
# 2. run_goal — miss → plan → candidate saved (not promoted)
# ---------------------------------------------------------------------------

async def test_run_goal_miss_calls_planner_and_saves_candidate(team):
    """run_goal on an empty store plans and saves a CANDIDATE (not promoted)."""
    store = InMemoryPlaybookStore()
    goal = "rotate cert and redeploy"

    fixed_plan = PlannedPlan(steps=[
        PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
        PlannedStep(instruction="Redeploy the service", needs="infra.deploy"),
    ])
    fake_client = _FakeClient(fixed_plan)

    run = await Workflow.run_goal(goal, team, store=store, client=fake_client)

    # Run completed
    assert run.status == "completed"

    # Playbook is a CANDIDATE — get() returns it
    pb = store.get(goal)
    assert pb is not None
    assert pb.name == goal

    # But it is NOT promoted — find() returns None for candidates
    assert store.find(goal) is None


async def test_run_goal_miss_no_store_still_runs(team):
    """run_goal with store=None runs the planned playbook without storing it."""
    goal = "rotate cert"
    fixed_plan = PlannedPlan(steps=[
        PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
    ])
    fake_client = _FakeClient(fixed_plan)

    run = await Workflow.run_goal(goal, team, store=None, client=fake_client)

    assert run.status == "completed"
    assert len(run.results) == 1


async def test_run_goal_without_client_derives_planner_client_from_team_model_config(monkeypatch):
    """run_goal derives the planner Client from team agents when client is omitted."""
    cert = await Agent.create(
        model="openai/qwen3.6-plus",
        api_base="https://opencode.ai/zen/go/v1",
        api_key="oc-test-key",
        name="cert-agent",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
    )
    deploy = await Agent.create(
        model="openai/qwen3.6-plus",
        api_base="https://opencode.ai/zen/go/v1",
        api_key="oc-test-key",
        name="deploy-agent",
        skills=[Skill("infra.deploy", description="deploy services")],
    )

    async def _fake_run(message: str, **kwargs) -> str:
        return f"ran: {message}"

    cert.run = _fake_run
    deploy.run = _fake_run
    team = Team([cert, deploy])

    captured: list[dict] = []

    class CapturingClient:
        def __init__(self, **kwargs) -> None:
            captured.append(kwargs)

        def structured(self, schema, prompt, **kwargs):
            return PlannedPlan(steps=[
                PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
                PlannedStep(instruction="Redeploy the service", needs="infra.deploy"),
            ])

    monkeypatch.setattr("coactra.ai.Client", CapturingClient)

    run = await Workflow.run_goal("rotate cert and redeploy", team)

    assert run.status == "completed"
    assert captured == [{
        "model": "openai/qwen3.6-plus",
        "api_base": "https://opencode.ai/zen/go/v1",
        "api_key": "oc-test-key",
    }]


async def test_run_goal_failed_run_does_not_save_candidate(team):
    """If the planned run fails, save_candidate must NOT be called."""
    store = InMemoryPlaybookStore()
    goal = "do quantum stuff"

    # Plan returns a needs that no agent can match
    fixed_plan = PlannedPlan(steps=[
        PlannedStep(instruction="Entangle qubits", needs="quantum.entanglement"),
    ])
    fake_client = _FakeClient(fixed_plan)

    run = await Workflow.run_goal(goal, team, store=store, client=fake_client)

    assert run.status == "failed"
    # Playbook must not have been stored
    assert store.get(goal) is None


# ---------------------------------------------------------------------------
# 3. Checkpoint after each step and at interrupt
# ---------------------------------------------------------------------------

async def test_checkpoint_saved_after_each_step(team):
    """run() with a CheckpointStore saves state after every completed step."""
    cp_store = InMemoryCheckpointStore()
    run_id = "chk-test-1"

    wf = Workflow("two-step", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("deploy the service", needs="infra.deploy"),
    ])
    run = await wf.run(team, checkpoint=cp_store, run_id=run_id)

    assert run.status == "completed"

    # Checkpoint must have been saved
    state = cp_store.load(run_id)
    assert state is not None

    # Reconstructed state has 2 completed results
    reconstructed = run_from_state(state)
    assert len(reconstructed.results) == 2
    assert all(r.status == "done" for r in reconstructed.results)


async def test_checkpoint_saved_at_interrupt(team):
    """run() with a CheckpointStore saves state when interrupted at an approval step."""
    cp_store = InMemoryCheckpointStore()
    run_id = "chk-test-interrupt"

    wf = Workflow("approval-wf", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("deploy the service", needs="infra.deploy", approve=True),
    ])
    interrupted = await wf.run(team, checkpoint=cp_store, run_id=run_id)

    assert interrupted.status == "interrupted"

    # Checkpoint must contain the saved state
    state = cp_store.load(run_id)
    assert state is not None

    reconstructed = run_from_state(state)
    # One step completed before interrupt
    assert len(reconstructed.results) == 1
    assert reconstructed.results[0].status == "done"
    assert reconstructed.status == "interrupted"
    assert reconstructed.pending_index == 1


async def test_no_checkpoint_store_run_still_works(team):
    """run() without a CheckpointStore behaves exactly as before (no regression)."""
    wf = Workflow("plain", steps=[
        step("rotate the cert", needs="cert rotation"),
    ])
    run = await wf.run(team)
    assert run.status == "completed"


# ---------------------------------------------------------------------------
# 4. resume_from — reconstruct from checkpoint and complete
# ---------------------------------------------------------------------------

async def test_resume_from_interrupted_approval_completes(team):
    """resume_from reconstructs from checkpoint and completes after approval."""
    cp_store = InMemoryCheckpointStore()
    run_id = "resume-test-1"

    wf = Workflow("approval-wf", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("deploy the service", needs="infra.deploy", approve=True),
    ])

    # Run until interrupted
    interrupted = await wf.run(team, checkpoint=cp_store, run_id=run_id)
    assert interrupted.status == "interrupted"

    # Resume from checkpoint with approval
    final = await wf.resume_from(cp_store, run_id, team, decision=True)

    assert final.status == "completed"
    assert len(final.results) == 2
    assert final.results[0].agent == "cert-agent"
    assert final.results[1].agent == "deploy-agent"
    assert final.results[1].status == "done"
    assert len(final.approvals) == 1
    assert final.approvals[0].decision is True


async def test_resume_from_interrupted_approval_denied(team):
    """resume_from with decision=False records the step as skipped (denied)."""
    cp_store = InMemoryCheckpointStore()
    run_id = "resume-denied"

    wf = Workflow("approval-wf", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("deploy the service", needs="infra.deploy", approve=True),
    ])

    interrupted = await wf.run(team, checkpoint=cp_store, run_id=run_id)
    assert interrupted.status == "interrupted"

    denied = await wf.resume_from(cp_store, run_id, team, decision=False)

    assert denied.status == "denied"
    assert len(denied.results) == 2
    assert denied.results[1].status == "skipped"
    assert denied.approvals[0].decision is False


async def test_resume_from_non_approval_run_continues(team):
    """resume_from on a non-interrupted run (e.g. status='running') continues from
    the last completed step index derived from len(results)."""
    cp_store = InMemoryCheckpointStore()
    run_id = "resume-mid"

    # Manually simulate a mid-run state (e.g. one step done, one remaining)
    from coactra.agent.workflow import StepResult, WorkflowRun
    from coactra.agent.checkpoint import run_to_state

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

    # Create matching workflow
    wf = Workflow("two-step", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("deploy the service", needs="infra.deploy"),
    ])

    final = await wf.resume_from(cp_store, run_id, team)
    assert final.status == "completed"
    assert len(final.results) == 2
    assert final.results[0].status == "done"   # pre-existing
    assert final.results[1].status == "done"   # newly run


async def test_resume_from_missing_checkpoint_raises(team):
    """resume_from raises ValueError when no checkpoint exists for the run_id."""
    cp_store = InMemoryCheckpointStore()

    wf = Workflow("any", steps=[step("do it", needs="cert rotation")])

    with pytest.raises((ValueError, KeyError)):
        await wf.resume_from(cp_store, "nonexistent-run-id", team)


# ---------------------------------------------------------------------------
# 5. Durable engine bridge — public Workflow delegates to old WorkflowEngine
# ---------------------------------------------------------------------------

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

    def match(self, needs: str):
        return self._members.get("alpha-agent")


async def test_public_workflow_runs_and_resumes_with_durable_langgraph_engine():
    pytest.importorskip("langgraph")
    from langgraph.checkpoint.memory import MemorySaver
    from coactra.workflow import DurableLangGraphEngine

    engine = DurableLangGraphEngine(checkpointer=MemorySaver())
    team = _BridgeTeam()
    wf = Workflow("public-durable", steps=[
        step("collect evidence", agent="alpha-agent"),
        step("apply change", agent="beta-agent", approve=True),
    ])

    paused = await wf.run(team, engine=engine, run_id="durable-bridge")

    assert paused.status == "interrupted"
    assert paused.pending_index == 1
    assert paused.thread_id == "acme:durable-bridge"
    assert [r.agent for r in paused.results] == ["alpha-agent"]

    final = await wf.resume_engine(engine, paused.thread_id, team, decision=True)

    assert final.status == "completed"
    assert [r.agent for r in final.results] == ["alpha-agent", "beta-agent"]
    assert [r.status for r in final.results] == ["done", "done"]
