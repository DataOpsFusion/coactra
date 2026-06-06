"""Workflow triage planner — LLM-driven Playbook generation.

Public API
----------
- ``PlannedStep``    — pydantic schema: one LLM-generated step (instruction + needs).
- ``PlannedPlan``    — pydantic schema: list of PlannedStep (LLM output envelope).
- ``plan_playbook``  — turn a goal + Team into a capability-routed Playbook.

Design notes
------------
``plan_playbook`` is intentionally a thin connector: it builds a roster description
from ``team.roster()``, constructs a prompt, and delegates all planning logic to the
LLM via ``client.structured()``.  The LLM decides the step decomposition; we just map
the response onto :class:`~coactra.agent.workflow.Step` / :class:`~coactra.agent.workflow.Playbook`.

``client`` is injectable (any object exposing ``.structured(schema, prompt)``).
When omitted, a :class:`coactra.ai.Client` is built lazily inside the function so
no network call happens in tests that supply a fake client.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from coactra.agent.workflow import Playbook, step as make_step

__all__ = ["PlannedStep", "PlannedPlan", "plan_playbook"]


# ---------------------------------------------------------------------------
# Pydantic schemas for structured LLM output
# ---------------------------------------------------------------------------

class PlannedStep(BaseModel):
    """One step produced by the planner LLM."""

    instruction: str
    """What the executing agent should do."""

    needs: str
    """Capability required — used by Team.match() for agent routing."""


class PlannedPlan(BaseModel):
    """Envelope returned by the planner LLM: an ordered list of steps."""

    steps: list[PlannedStep]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(goal: str, cards: list[dict]) -> str:
    """Construct the planning prompt from the goal and team roster cards.

    Each card is an A2A Agent Card dict with a ``"skills"`` list.  We serialise
    the skill ``id`` and ``description`` so the LLM can reference them in the
    ``needs`` field of each step.
    """
    roster_lines: list[str] = []
    for card in cards:
        agent_name = card.get("name", "unknown")
        for skill in card.get("skills", []):
            skill_id = skill.get("id", "")
            description = skill.get("description", "")
            roster_lines.append(f"  - agent={agent_name} skill_id={skill_id}: {description}")

    roster_text = "\n".join(roster_lines) if roster_lines else "  (no agents available)"

    return (
        f"You are a workflow planner. Break the following goal into an ordered list of steps.\n"
        f"Each step must have:\n"
        f"  - instruction: a clear, actionable instruction for the executing agent\n"
        f"  - needs: the skill_id from the roster that best covers this step\n\n"
        f"Goal: {goal}\n\n"
        f"Available agents and skills:\n{roster_text}\n\n"
        f"Return a JSON object matching the PlannedPlan schema: "
        f'{{\"steps\": [{{\"instruction\": \"...\", \"needs\": \"skill_id\"}}]}}'
    )


# ---------------------------------------------------------------------------
# plan_playbook
# ---------------------------------------------------------------------------

def plan_playbook(
    goal: str,
    team: Any,
    *,
    client: Any = None,
) -> Playbook:
    """Turn a *goal* into a :class:`~coactra.agent.workflow.Playbook` of capability-routed steps.

    Parameters
    ----------
    goal:
        Plain-language description of what needs to be accomplished.
    team:
        A :class:`~coactra.agent.team.Team` (duck-typed: needs ``.roster() -> list[dict]``).
        ``roster()`` is called to build the agent/skill description for the LLM prompt.
    client:
        Injectable LLM client exposing ``.structured(schema, prompt) -> PlannedPlan``.
        When ``None``, a default :class:`coactra.ai.Client` is constructed lazily so
        tests that inject a fake client never trigger a network call.

    Returns
    -------
    :class:`~coactra.agent.workflow.Playbook`
        A Playbook whose name equals *goal* and whose steps are capability-routed
        (``needs`` set) ready for :class:`~coactra.agent.workflow.Workflow` execution.
    """
    if client is None:
        from coactra.ai import Client  # lazy import — not triggered when fake injected
        client = Client(model="gpt-4o-mini")

    cards = team.roster()
    prompt = _build_prompt(goal, cards)

    planned: PlannedPlan = client.structured(PlannedPlan, prompt)

    steps = [
        make_step(s.instruction, needs=s.needs)
        for s in planned.steps
    ]

    return Playbook(name=goal, steps=steps)
