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
from coactra.workflow.playbook import ProofBundle, VerificationReceipt


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

    final = await wf.resume(interrupted, team, decision=True, proof_bundle=_proof_bundle())

    assert final.status == "completed"
    assert len(final.results) == 2
    assert final.results[1].agent == "sre-agent"
    assert final.results[1].status == "done"
    assert len(final.approvals) == 1
    assert final.approvals[0].decision is True
    assert final.approvals[0].proof_bundle is not None


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
            step("rotate the cert", requires_skill="cert.rotate", required_tags=["tls"]),
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
    assert pb2.steps[0].required_tags == pb.steps[0].required_tags
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


async def test_required_tags_disambiguate_shared_skill():
    from coactra.agent.workflow import Workflow, step

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
                    capability="review",
                    profile=ModelProfile(name="review", model=_make_echo_model("review-agent")),
                ),
            ]
        ),
    )
    await team.add_agent(
        name="security-agent",
        model_capability="security",
        skills=[Skill("python", tags=["implement", "backend"])],
        expose=True,
    )
    await team.add_agent(
        name="review-agent",
        model_capability="review",
        skills=[Skill("python", tags=["security", "review"])],
        expose=True,
    )

    wf = Workflow(
        "tagged-route",
        steps=[
            step(
                "review the patch",
                requires_skill="python",
                required_tags=["security"],
            )
        ],
    )
    run = await wf.run(team)

    assert run.status == "completed"
    assert run.results[0].agent == "review-agent"


async def test_ambiguous_skill_without_tags_fails_closed():
    from coactra.agent.workflow import Workflow, step

    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="a",
                    profile=ModelProfile(name="a", model=_make_echo_model("agent-a")),
                ),
                ModelRoute(
                    capability="b",
                    profile=ModelProfile(name="b", model=_make_echo_model("agent-b")),
                ),
            ]
        ),
    )
    await team.add_agent(
        name="agent-a",
        model_capability="a",
        skills=[Skill("python", tags=["backend"])],
        expose=True,
    )
    await team.add_agent(
        name="agent-b",
        model_capability="b",
        skills=[Skill("python", tags=["security"])],
        expose=True,
    )

    wf = Workflow(
        "ambiguous-route",
        steps=[step("handle python task", requires_skill="python")],
    )
    run = await wf.run(team)

    assert run.status == "failed"


async def test_workflow_checks_policy_at_route_and_execute():
    from coactra.agent.workflow import Workflow, step

    observed = Policy.observed()
    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=observed,
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="sre",
                    profile=ModelProfile(
                        name="sre",
                        model=_make_echo_model("sre-agent"),
                    ),
                )
            ]
        ),
    )
    await team.add_agent(
        name="sre-agent",
        model_capability="sre",
        skills=[Skill("infra.deploy", tags=["deploy"])],
        expose=True,
    )

    wf = Workflow("policy-check", steps=[step("deploy", requires_skill="infra.deploy")])
    run = await wf.run(team)

    assert run.status == "completed"
    actions = [request.action for request in observed.decisions if request.component == "team"]
    assert "workflow.route" in actions
    assert "workflow.execute" in actions


async def test_approval_only_gate_records_human_decision_and_continues(team):
    from coactra.agent.workflow import Workflow, step

    wf = Workflow(
        "approval-only",
        steps=[
            step("rotate the cert", requires_skill="cert.rotate"),
            step("approve the verified change", approve=True, approval_only=True),
            step("redeploy the service", requires_skill="infra.deploy"),
        ],
    )
    interrupted = await wf.run(team)

    assert interrupted.status == "interrupted"
    assert interrupted.pending_index == 1
    assert len(interrupted.results) == 1

    final = await wf.resume(interrupted, team, decision=True, proof_bundle=_proof_bundle())

    assert final.status == "completed"
    assert [result.agent for result in final.results] == ["security-agent", "sre-agent"]
    assert len(final.approvals) == 1
    assert final.approvals[0].proof_bundle is not None


async def test_code_change_builder_returns_workflow_and_contracts():
    from coactra.agent.workflow import (
        CodeChangeRiskTier,
        VerificationCheck,
        VerifierRequirement,
        VerifierRole,
        Workflow,
    )

    plan = Workflow.code_change(
        "website-maintenance",
        implement_instruction="Update the website configuration safely.",
        implement_skill="ops",
        verifier_roles=[
            VerifierRole(
                role="functional",
                skill="ops",
                required_tags=["health"],
                checks=[
                    VerificationCheck(
                        id="healthz",
                        kind="http",
                        instruction="GET /healthz and confirm 200",
                    )
                ],
            ),
            VerifierRole(
                role="security",
                skill="security",
                requirement=VerifierRequirement.advisory,
                checks=[
                    VerificationCheck(
                        id="headers",
                        kind="state",
                        instruction="Confirm security headers remain configured.",
                    )
                ],
            ),
        ],
        review_skill="review",
        review_tags=["change-review"],
        risk_tier=CodeChangeRiskTier.high,
    )

    assert plan.risk_tier is CodeChangeRiskTier.high
    assert plan.requires_human_approval is True
    assert plan.verification_bundle_type.__name__ == "CodeChangeVerificationBundle"
    assert plan.review_decision_type.__name__ == "CodeChangeReviewDecision"
    assert plan.workflow.name == "website-maintenance"
    assert len(plan.workflow._playbook.steps) == 5
    assert plan.workflow._playbook.steps[1].requires_skill == "ops"
    assert plan.workflow._playbook.steps[1].required_tags == ("health",)
    assert plan.workflow._playbook.steps[-1].approval_only is True
    assert plan.workflow._playbook.steps[-1].approve is True


async def test_code_change_builder_low_risk_can_skip_human_gate():
    from coactra.agent.workflow import CodeChangeRiskTier, VerificationCheck, VerifierRole, Workflow

    plan = Workflow.code_change(
        "small-fix",
        implement_instruction="Apply a small safe change.",
        implement_agent="implementer",
        verifier_roles=[
            VerifierRole(
                role="functional",
                agent="verifier",
                checks=[
                    VerificationCheck(
                        id="smoke",
                        kind="command",
                        instruction="Run the smoke test.",
                    )
                ],
            )
        ],
        review_agent="reviewer",
        risk_tier=CodeChangeRiskTier.low,
        human_approval="auto",
    )

    assert plan.requires_human_approval is False
    assert len(plan.workflow._playbook.steps) == 3
