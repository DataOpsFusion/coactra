"""Live acceptance — a real Team runs a Workflow against opencode-zen.

Env-gated (skips cleanly without a key, like test_live_zen). Proves the design
end-to-end: capability routing, approval pause/resume, durable checkpoint/resume,
run_goal triage with the real planner, and peer delegation. Deterministic parts
(routing/approval/durable) are hard-asserted; LLM-dependent parts (planner output,
peer) are asserted loosely (>=1 step / non-empty).

Run:  OC_KEY=... .venv/bin/python -m pytest tests/agent/test_acceptance_live.py -q -s
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from coactra import Agent, Team, Workflow, step, Skill
from coactra.ai import Client
from coactra.agent.playbook_store import InMemoryPlaybookStore
from coactra.agent.checkpoint import InMemoryCheckpointStore

ZEN = "https://opencode.ai/zen/go/v1"
MODEL = "openai/qwen3.6-plus"
_KEY_FILE = Path("/tmp/oc.key")


def _key() -> str | None:
    return os.environ.get("OC_KEY") or (_KEY_FILE.read_text().strip() if _KEY_FILE.exists() else None)


live = pytest.mark.skipif(_key() is None, reason="no opencode key (OC_KEY or /tmp/oc.key)")


async def _agent(name, skills, instr):
    return await Agent.create(model=MODEL, api_base=ZEN, api_key=_key(),
                              name=name, tenant="acme", skills=skills, instructions=instr)


@live
async def test_team_workflow_acceptance():
    security = await _agent("security-agent",
                            [Skill("cert.rotate", description="rotate TLS certificates and manage vault secrets")],
                            "You rotate TLS certs. Be terse.")
    sre = await _agent("sre-agent",
                       [Skill("deploy", description="redeploy services, restart nginx, run deployments")],
                       "You redeploy services. Be terse.")
    team = Team([security, sre])

    # 1) capability routing + approval pause/resume (deterministic asserts)
    play = Workflow("rotate-and-redeploy", steps=[
        step("Rotate the production TLS certificate.", needs="cert rotation"),
        step("Redeploy nginx to pick up the new certificate.", needs="deploy", approve=True),
    ])
    run = await play.run(team)
    assert run.status == "interrupted"
    assert run.results[0].agent == "security-agent"
    done = await play.resume(run, team, decision=True)
    assert done.status == "completed"
    assert done.results[1].agent == "sre-agent"

    # 2) durable checkpoint + resume across a simulated restart
    ck = InMemoryCheckpointStore()
    play2 = Workflow("durable", steps=[
        step("Rotate the prod TLS cert.", needs="cert rotation"),
        step("Redeploy nginx.", needs="deploy", approve=True),
    ])
    r2 = await play2.run(team, checkpoint=ck, run_id="acc-2")
    assert r2.status == "interrupted"
    assert ck.load("acc-2") is not None
    r2b = await play2.resume_from(ck, "acc-2", team, decision=True)
    assert r2b.status == "completed"

    # 3) run_goal triage with the real planner (LLM-dependent → loose assert)
    store = InMemoryPlaybookStore()
    r3 = await Workflow.run_goal(
        "Rotate the production TLS certificate, then redeploy nginx.", team,
        store=store, client=Client(model=MODEL, api_base=ZEN, api_key=_key()))
    assert len(r3.results) >= 1

    # 4) peer delegation (deterministic tool invocation)
    mgr = await Agent.create(model=MODEL, api_base=ZEN, api_key=_key(),
                             name="manager", tenant="acme", peers=[security])
    ask = next((t for t in mgr._tools if getattr(t, "__name__", "") == "ask_security_agent"), None)
    assert ask is not None
    out = await ask("Rotate the prod cert and report what you did.")
    assert out and out.strip()
