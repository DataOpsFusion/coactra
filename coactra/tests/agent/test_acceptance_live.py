"""Live acceptance — a real Team runs a Workflow against opencode-zen.

Env-gated (skips cleanly without a key, like test_live_zen). Proves the design
end-to-end: Team-owned agent assembly, exact skill routing, approval pause/resume,
durable checkpoint/resume, and peer delegation.
Deterministic parts are hard-asserted; LLM-dependent parts are asserted loosely.

Run:  OC_KEY=... .venv/bin/python -m pytest tests/agent/test_acceptance_live.py -q -s
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team, Workflow
from coactra.agent.checkpoint import InMemoryCheckpointStore
from coactra.workflow import ProofBundle, VerificationReceipt, step


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

ZEN = os.getenv("OPENCODE_ZEN_BASE", "https://opencode.ai/zen/go/v1")
_KEY_FILES = (Path("/tmp/OC.key"), Path("/tmp/oc.key"))


def _key() -> str | None:
    for key_file in _KEY_FILES:
        if key_file.exists():
            return key_file.read_text().strip()
    return os.environ.get("OC_KEY")


pytestmark = pytest.mark.live
live = pytest.mark.skipif(
    _key() is None,
    reason="no opencode key (/tmp/OC.key, /tmp/oc.key, or OC_KEY)",
)


def _zen_model():
    provider = OpenAIProvider(base_url=ZEN, api_key=_key())
    return OpenAIChatModel("deepseek-v4-pro", provider=provider)


@live
async def test_team_workflow_acceptance():
    team = Team(
        scope=Scope(tenant_id="acme", namespace="prod"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="security", profile=ModelProfile(name="security", model=_zen_model())
                ),
                ModelRoute(capability="sre", profile=ModelProfile(name="sre", model=_zen_model())),
            ]
        ),
    )
    security = await team.add_agent(
        name="security-agent",
        model_capability="security",
        skills=[
            Skill(
                "cert.rotate",
                description="rotate TLS certificates and manage vault secrets",
            )
        ],
        instructions="You rotate TLS certs. Be terse.",
        expose=True,
    )
    await team.add_agent(
        name="sre-agent",
        model_capability="sre",
        skills=[
            Skill(
                "infra.deploy",
                description="redeploy services, restart nginx, run deployments",
            )
        ],
        instructions="You redeploy services. Be terse.",
        expose=True,
    )

    play = Workflow(
        "rotate-and-redeploy",
        steps=[
            step("Rotate the production TLS certificate.", requires_skill="cert.rotate"),
            step(
                "Redeploy nginx to pick up the new certificate.",
                requires_skill="infra.deploy",
                approve=True,
            ),
        ],
    )
    run = await play.run(team)
    assert run.status == "interrupted"
    assert run.results[0].agent == "security-agent"
    done = await play.resume(run, team, decision=True, proof_bundle=_proof_bundle())
    assert done.status == "completed"
    assert done.results[1].agent == "sre-agent"

    ck = InMemoryCheckpointStore()
    play2 = Workflow(
        "durable",
        steps=[
            step("Rotate the prod TLS cert.", requires_skill="cert.rotate"),
            step("Redeploy nginx.", requires_skill="infra.deploy", approve=True),
        ],
    )
    r2 = await play2.run(team, checkpoint=ck, run_id="acc-2")
    assert r2.status == "interrupted"
    assert ck.load("acc-2") is not None
    r2b = await play2.resume_from(ck, "acc-2", team, decision=True, proof_bundle=_proof_bundle())
    assert r2b.status == "completed"

    mgr_team = Team(
        scope=Scope(tenant_id="acme", namespace="prod-manager"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="manager", profile=ModelProfile(name="manager", model=_zen_model())
                )
            ]
        ),
    )
    mgr = await mgr_team.add_agent(model_capability="manager", name="manager", peers=[security])
    ask = next((t for t in mgr._tools if getattr(t, "__name__", "") == "ask_security_agent"), None)
    assert ask is not None
    out = await ask("Rotate the prod cert and report what you did.")
    assert out and out.strip()
