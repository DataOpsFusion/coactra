"""Small live workflow smoke check against OpenCode.

Env-gated; skips cleanly without a key.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team, Workflow
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


OPENCODE_BASE = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/go/v1")
_KEY_FILES = (Path("/tmp/OC.key"), Path("/tmp/oc.key"))


def _opencode_key() -> str | None:
    for key_file in _KEY_FILES:
        if key_file.exists():
            return key_file.read_text().strip()
    return os.environ.get("OC_KEY") or os.environ.get("API_KEY")


pytestmark = pytest.mark.live
live = pytest.mark.skipif(
    _opencode_key() is None,
    reason="no opencode key (/tmp/OC.key, /tmp/oc.key, or OC_KEY)",
)


def _opencode_model():
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    provider = OpenAIProvider(base_url=OPENCODE_BASE, api_key=_opencode_key())
    return OpenAIChatModel("deepseek-v4-pro", provider=provider)


@live
async def test_opencode_model_runs_workflow_and_resumes_approval():
    team = Team(
        scope=Scope(tenant_id="acme", namespace="live"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="security",
                    profile=ModelProfile(name="security", model=_opencode_model()),
                ),
            ]
        ),
    )
    await team.add_agent(
        name="security-agent",
        model_capability="security",
        skills=[
            Skill(
                "cert.rotate",
                description="rotate demo TLS certificates",
            )
        ],
        instructions="Rotate demo TLS certificates. Be terse.",
    )

    play = Workflow(
        "rotate-demo-certificate",
        steps=[
            step("Rotate the demo TLS certificate.", requires_skill="cert.rotate"),
            step(
                "Approve the verified demo change.",
                approve=True,
                approval_only=True,
            ),
        ],
    )
    interrupted = await play.run(team)

    assert interrupted.status == "interrupted"
    assert interrupted.pending_index == 1
    assert interrupted.results[0].agent == "security-agent"
    assert interrupted.results[0].output.strip()

    done = await play.resume(interrupted, team, decision=True, proof_bundle=_proof_bundle())

    assert done.status == "completed"
    assert len(done.results) == 1
    assert done.approvals[0].decision is True
