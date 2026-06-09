"""TDD tests for core Workflow — Playbook data-core, step(), run/resume over Team.

Covers:
1. Skill routing — step.requires_skill matches the correct agent by skill id
2. Pin by name — step.agent resolves to named agent directly
3. Approval pause/resume — approve=True pauses; resume(decision=True) continues;
   resume(decision=False) skips/denies
4. Data core — Playbook round-trips through to_dict/from_dict; from_yaml loads
5. Unresolvable step — failed status, ledger records failure, no crash
"""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope
from coactra.agent.skills import Skill
from coactra.team import Team


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


@pytest.fixture
async def team():
    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="security",
                    profile=ModelProfile(name="security", model=_make_echo_model("security-agent")),
                ),
                ModelRoute(
                    capability="sre",
                    profile=ModelProfile(name="sre", model=_make_echo_model("sre-agent")),
                ),
            ]
        ),
    )
    await team.add_agent(
        name="security-agent",
        model_capability="security",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
        expose=True,
    )
    await team.add_agent(
        name="sre-agent",
        model_capability="sre",
        skills=[Skill("infra.deploy", description="redeploy services")],
        expose=True,
    )
    return team


async def test_skill_routing_two_steps(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow(
        "route-test",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("redeploy the service", requires_skill="infra.deploy"),
        ],
    )
    run = await wf.run(team)

    assert run.status == "completed"
    assert len(run.results) == 2
    assert run.results[0].agent == "security-agent"
    assert run.results[0].status == "done"
    assert run.results[1].agent == "sre-agent"
    assert run.results[1].status == "done"


async def test_pin_by_name(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("pin-test", steps=[step("do it", agent="sre-agent")])
    run = await wf.run(team)

    assert run.status == "completed"
    assert run.results[0].agent == "sre-agent"
    assert run.results[0].status == "done"


async def test_approval_pauses_before_running_step(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow(
        "approve-test",
        steps=[step("redeploy the service", requires_skill="infra.deploy", approve=True)],
    )
    run = await wf.run(team)

    assert run.status == "interrupted"
    assert run.pending_index == 0
    assert len(run.results) == 0


async def test_approval_resume_true_completes(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow(
        "approve-resume-true",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("redeploy the service", requires_skill="infra.deploy", approve=True),
        ],
    )
    interrupted = await wf.run(team)

    assert interrupted.status == "interrupted"
    assert interrupted.pending_index == 1
    assert len(interrupted.results) == 1
    assert interrupted.results[0].agent == "security-agent"

    final = await wf.resume(interrupted, team, decision=True)

    assert final.status == "completed"
    assert len(final.results) == 2
    assert final.results[1].agent == "sre-agent"
    assert final.results[1].status == "done"
    assert len(final.approvals) == 1
    assert final.approvals[0].decision is True


async def test_approval_resume_false_denies(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow(
        "approve-resume-false",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("redeploy the service", requires_skill="infra.deploy", approve=True),
        ],
    )
    interrupted = await wf.run(team)
    assert interrupted.status == "interrupted"

    denied = await wf.resume(interrupted, team, decision=False)

    assert denied.status == "denied"
    assert len(denied.results) == 2
    assert denied.results[1].status == "skipped"
    assert len(denied.approvals) == 1
    assert denied.approvals[0].decision is False


async def test_approval_pending_step_accessible(team):
    from coactra.agent.workflow import Step, Workflow, step

    wf = Workflow(
        "pending-step-test",
        steps=[step("redeploy the service", requires_skill="infra.deploy", approve=True)],
    )
    run = await wf.run(team)

    assert run.status == "interrupted"
    ps = run.pending_step
    assert ps is not None
    assert isinstance(ps, Step)
    assert ps.approve is True


def test_playbook_to_dict_from_dict_round_trip():
    from coactra.workflow.playbook import Playbook, step

    pb = Playbook(
        name="cert-rotation",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("redeploy", agent="sre-agent", approve=True),
        ],
    )
    d = pb.to_dict()

    assert d["name"] == "cert-rotation"
    assert len(d["steps"]) == 2
    assert d["steps"][0]["instruction"] == "rotate the cert"
    assert d["steps"][0]["requires_skill"] == "cert.rotate"
    assert d["steps"][1]["agent"] == "sre-agent"
    assert d["steps"][1]["approve"] is True

    pb2 = Playbook.from_dict(d)
    assert pb2.name == pb.name
    assert len(pb2.steps) == len(pb.steps)
    assert pb2.steps[0].instruction == pb.steps[0].instruction
    assert pb2.steps[0].requires_skill == pb.steps[0].requires_skill
    assert pb2.steps[1].agent == pb.steps[1].agent
    assert pb2.steps[1].approve == pb.steps[1].approve


async def test_playbook_from_yaml_runs(team):
    from coactra.agent.workflow import Workflow
    from coactra.workflow.playbook import Playbook

    yaml_text = """\
name: yaml-cert-rotation
steps:
  - instruction: rotate the cert
    requires_skill: cert.rotate
  - instruction: redeploy the service
    requires_skill: infra.deploy
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
    from coactra.agent.workflow import Workflow

    yaml_text = """\
name: yaml-workflow
steps:
  - instruction: redeploy the service
    requires_skill: infra.deploy
"""
    wf = Workflow.from_yaml(yaml_text)
    run = await wf.run(team)
    assert run.status == "completed"
    assert run.results[0].status == "done"


async def test_unresolvable_requires_skill_fails(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow(
        "unresolvable",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("do quantum stuff", requires_skill="quantum.entanglement"),
        ],
    )
    run = await wf.run(team)

    assert run.status == "failed"
    assert run.results[0].status == "done"
    assert run.results[1].status == "failed"
    assert run.results[1].agent == ""


async def test_unresolvable_agent_name_fails(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow("bad-name", steps=[step("do it", agent="nonexistent-agent")])
    run = await wf.run(team)

    assert run.status == "failed"
    assert run.results[0].status == "failed"


def test_workflow_and_step_importable_from_workflow_package():
    from coactra import Workflow
    from coactra.workflow import step

    assert Workflow is not None
    assert step is not None


def test_workflow_import_does_not_pull_pydantic_ai():
    import coactra.agent.workflow as wf_mod

    with open(wf_mod.__file__) as f:
        source = f.read()
    assert "from pydantic_ai" not in source
    assert "import pydantic_ai" not in source


async def test_workflow_run_output_texts(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow(
        "ledger-test",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("redeploy the service", requires_skill="infra.deploy"),
        ],
    )
    run = await wf.run(team)

    texts = run.output_texts()
    assert len(texts) == 2
    assert all(isinstance(t, str) for t in texts)
