"""TDD tests for core Workflow — Playbook data-core, step(), run/resume over Team.

RED phase: all tests written before implementation exists.

Covers:
1. Capability routing — step.needs matches agent by skill overlap
2. Pin by name — step.agent resolves to named agent directly
3. Approval pause/resume — approve=True pauses; resume(decision=True) continues;
   resume(decision=False) skips/denies
4. Data core — Playbook round-trips through to_dict/from_dict; from_yaml loads
5. Unresolvable step — failed status, ledger records failure, no crash
"""
from __future__ import annotations

import pytest
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart

from coactra.agent import Agent
from coactra.agent.skills import Skill
from coactra.agent.team import Team


# ---------------------------------------------------------------------------
# FunctionModel helpers — echo the instruction so we can assert routing
# ---------------------------------------------------------------------------

def _make_echo_model(label: str):
    """Return a FunctionModel that echoes '<label>: <prompt>'."""
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        # The last user message is the instruction
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def security_agent():
    return await Agent.create(
        model=_make_echo_model("security-agent"),
        name="security-agent",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
    )


@pytest.fixture
async def sre_agent():
    return await Agent.create(
        model=_make_echo_model("sre-agent"),
        name="sre-agent",
        skills=[Skill("deploy", description="redeploy services")],
    )


@pytest.fixture
def team(security_agent, sre_agent):
    return Team([security_agent, sre_agent])


# ---------------------------------------------------------------------------
# 1. Capability routing
# ---------------------------------------------------------------------------

async def test_capability_routing_two_steps(team, security_agent, sre_agent):
    """A 2-step playbook routes each step to the correct agent by capability."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("route-test", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("redeploy the service", needs="deploy"),
    ])
    run = await wf.run(team)

    assert run.status == "completed"
    assert len(run.results) == 2

    # Step 1 → security-agent (cert rotation)
    assert run.results[0].agent == "security-agent"
    assert run.results[0].status == "done"

    # Step 2 → sre-agent (deploy)
    assert run.results[1].agent == "sre-agent"
    assert run.results[1].status == "done"


# ---------------------------------------------------------------------------
# 2. Pin by name
# ---------------------------------------------------------------------------

async def test_pin_by_name(team, sre_agent):
    """step(agent='sre-agent') resolves to sre-agent regardless of needs."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("pin-test", steps=[
        step("do it", agent="sre-agent"),
    ])
    run = await wf.run(team)

    assert run.status == "completed"
    assert run.results[0].agent == "sre-agent"
    assert run.results[0].status == "done"


# ---------------------------------------------------------------------------
# 3. Approval pause / resume
# ---------------------------------------------------------------------------

async def test_approval_pauses_before_running_step(team):
    """approve=True causes run() to return interrupted before executing the step."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("approve-test", steps=[
        step("redeploy the service", needs="deploy", approve=True),
    ])
    run = await wf.run(team)

    # Must be interrupted — the step has NOT run yet
    assert run.status == "interrupted"
    assert run.pending_index == 0
    # The approval step has not produced output yet
    assert len(run.results) == 0


async def test_approval_resume_true_completes(team):
    """resume(decision=True) runs the paused step and completes the workflow."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("approve-resume-true", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("redeploy the service", needs="deploy", approve=True),
    ])
    interrupted = await wf.run(team)

    assert interrupted.status == "interrupted"
    assert interrupted.pending_index == 1  # second step paused

    # Step 0 already ran; 1 step in ledger so far
    assert len(interrupted.results) == 1
    assert interrupted.results[0].agent == "security-agent"

    # Resume with approval
    final = await wf.resume(interrupted, team, decision=True)

    assert final.status == "completed"
    # Both steps in ledger
    assert len(final.results) == 2
    assert final.results[1].agent == "sre-agent"
    assert final.results[1].status == "done"
    # Approval decision is recorded
    assert len(final.approvals) == 1
    assert final.approvals[0].decision is True


async def test_approval_resume_false_denies(team):
    """resume(decision=False) records the step as skipped and stops (status='denied')."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("approve-resume-false", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("redeploy the service", needs="deploy", approve=True),
    ])
    interrupted = await wf.run(team)
    assert interrupted.status == "interrupted"

    denied = await wf.resume(interrupted, team, decision=False)

    assert denied.status == "denied"
    # The approval step is recorded as skipped
    assert len(denied.results) == 2
    assert denied.results[1].status == "skipped"
    # Denial decision is recorded
    assert len(denied.approvals) == 1
    assert denied.approvals[0].decision is False


async def test_approval_pending_step_accessible(team):
    """WorkflowRun.pending_step returns the Step that is awaiting approval."""
    from coactra.agent.workflow import Workflow, step, Step

    wf = Workflow("pending-step-test", steps=[
        step("redeploy the service", needs="deploy", approve=True),
    ])
    run = await wf.run(team)

    assert run.status == "interrupted"
    ps = run.pending_step
    assert ps is not None
    assert isinstance(ps, Step)
    assert ps.approve is True


# ---------------------------------------------------------------------------
# 4. Data core — Playbook round-trip + YAML load
# ---------------------------------------------------------------------------

def test_playbook_to_dict_from_dict_round_trip():
    """Playbook round-trips through to_dict/from_dict without data loss."""
    from coactra.agent.workflow import Playbook, step

    pb = Playbook(name="cert-rotation", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("redeploy", agent="sre-agent", approve=True),
    ])
    d = pb.to_dict()

    # Canonical dict is plain data
    assert d["name"] == "cert-rotation"
    assert len(d["steps"]) == 2
    assert d["steps"][0]["instruction"] == "rotate the cert"
    assert d["steps"][0]["needs"] == "cert rotation"
    assert d["steps"][1]["agent"] == "sre-agent"
    assert d["steps"][1]["approve"] is True

    # Round-trip
    pb2 = Playbook.from_dict(d)
    assert pb2.name == pb.name
    assert len(pb2.steps) == len(pb.steps)
    assert pb2.steps[0].instruction == pb.steps[0].instruction
    assert pb2.steps[0].needs == pb.steps[0].needs
    assert pb2.steps[1].agent == pb.steps[1].agent
    assert pb2.steps[1].approve == pb.steps[1].approve


async def test_playbook_from_yaml_runs(team):
    """from_yaml loads a small YAML playbook and runs it end-to-end."""
    from coactra.agent.workflow import Playbook, Workflow

    yaml_text = """\
name: yaml-cert-rotation
steps:
  - instruction: rotate the cert
    needs: cert rotation
  - instruction: redeploy the service
    needs: deploy
"""
    pb = Playbook.from_yaml(yaml_text)
    assert pb.name == "yaml-cert-rotation"
    assert len(pb.steps) == 2

    wf = Workflow.from_playbook(pb)
    run = await wf.run(team)
    assert run.status == "completed"
    assert run.results[0].agent == "security-agent"
    assert run.results[1].agent == "sre-agent"


async def test_workflow_from_yaml(team):
    """Workflow.from_yaml convenience method loads and runs cleanly."""
    from coactra.agent.workflow import Workflow

    yaml_text = """\
name: yaml-workflow
steps:
  - instruction: redeploy the service
    needs: deploy
"""
    wf = Workflow.from_yaml(yaml_text)
    run = await wf.run(team)
    assert run.status == "completed"
    assert run.results[0].status == "done"


# ---------------------------------------------------------------------------
# 5. Unresolvable step
# ---------------------------------------------------------------------------

async def test_unresolvable_needs_fails(team):
    """A needs= that no agent matches → status='failed', ledger records failure."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("unresolvable", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("do quantum stuff", needs="quantum entanglement"),
    ])
    run = await wf.run(team)

    assert run.status == "failed"
    # First step succeeded, second failed
    assert run.results[0].status == "done"
    assert run.results[1].status == "failed"
    assert run.results[1].agent == ""  # no agent resolved


async def test_unresolvable_agent_name_fails(team):
    """An agent= name that doesn't exist → status='failed'."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("bad-name", steps=[
        step("do it", agent="nonexistent-agent"),
    ])
    run = await wf.run(team)

    assert run.status == "failed"
    assert run.results[0].status == "failed"


# ---------------------------------------------------------------------------
# 6. Top-level import gate
# ---------------------------------------------------------------------------

def test_workflow_and_step_importable_from_coactra():
    """from coactra import Workflow, step must work at the top level."""
    import coactra
    W = coactra.Workflow
    s = coactra.step
    assert W is not None
    assert s is not None


def test_workflow_import_does_not_pull_pydantic_ai():
    """Importing coactra.agent.workflow must NOT pull pydantic_ai."""
    import importlib
    import coactra.agent.workflow as wf_mod
    with open(wf_mod.__file__) as f:
        source = f.read()
    assert "from pydantic_ai" not in source
    assert "import pydantic_ai" not in source


# ---------------------------------------------------------------------------
# 7. WorkflowRun ledger accessor
# ---------------------------------------------------------------------------

async def test_workflow_run_output_texts(team):
    """WorkflowRun provides a clean accessor for all output texts."""
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("ledger-test", steps=[
        step("rotate the cert", needs="cert rotation"),
        step("redeploy the service", needs="deploy"),
    ])
    run = await wf.run(team)

    texts = run.output_texts()
    assert len(texts) == 2
    assert all(isinstance(t, str) for t in texts)
