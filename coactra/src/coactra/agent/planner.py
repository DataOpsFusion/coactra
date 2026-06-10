"""Workflow triage planner — LLM-driven Playbook generation.

Public API
----------
- ``PlannedStep``    — pydantic schema: one LLM-generated step (instruction + requires_skill + required_tags).
- ``PlannedPlan``    — pydantic schema: list of PlannedStep (LLM output envelope).
- ``plan_playbook``  — turn a goal + Team into a skill-routed Playbook.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from coactra.workflow.playbook import Playbook
from coactra.workflow.playbook import step as make_step

__all__ = ["PlannedStep", "PlannedPlan", "plan_playbook"]


class PlannedStep(BaseModel):
    """One step produced by the planner LLM."""

    instruction: str
    requires_skill: str
    required_tags: list[str] = Field(default_factory=list)


class PlannedPlan(BaseModel):
    """Envelope returned by the planner LLM: an ordered list of steps."""

    steps: list[PlannedStep]


def _build_prompt(goal: str, cards: list[dict]) -> str:
    """Construct the planning prompt from the goal and team roster cards."""
    roster_lines: list[str] = []
    for card in cards:
        agent_name = card.get("name", "unknown")
        for skill in card.get("skills", []):
            skill_id = skill.get("id", "")
            description = skill.get("description", "")
            tags = ",".join(skill.get("tags", [])) or "-"
            roster_lines.append(
                f"  - agent={agent_name} skill_id={skill_id} tags={tags}: {description}"
            )

    roster_text = "\n".join(roster_lines) if roster_lines else "  (no agents available)"

    return (
        "You are a workflow planner. Break the following goal into an ordered list of steps.\n"
        "Each step must have:\n"
        "  - instruction: a clear, actionable instruction for the executing agent\n"
        "  - requires_skill: the broad skill_id from the roster that best covers this step\n"
        "  - required_tags: optional tags that disambiguate agents sharing the same skill_id\n\n"
        f"Goal: {goal}\n\n"
        f"Available agents and skills:\n{roster_text}\n\n"
        "Return a JSON object matching the PlannedPlan schema: "
        '{"steps": [{"instruction": "...", "requires_skill": "skill_id", "required_tags": ["tag"]}]}'
    )


def _planner_client_from_team(team: Any) -> Any:
    """Build the default planner client from the first team agent model config."""
    from coactra.ai import Client

    members = getattr(team, "_members", [])
    if isinstance(members, dict):
        members = list(members.values())

    for member in members:
        runtime = getattr(member, "_runtime", None)
        config = dict(getattr(runtime, "_model_config", None) or {})
        model_id = config.pop("model", None)
        if not isinstance(model_id, str) or not model_id:
            continue
        return Client(model=model_id, **config)

    return Client(model="gpt-4o-mini")


def plan_playbook(
    goal: str,
    team: Any,
    *,
    client: Any = None,
) -> Playbook:
    """Turn a goal into a skill-routed :class:`Playbook`."""
    if client is None:
        client = _planner_client_from_team(team)

    cards = team.roster()
    prompt = _build_prompt(goal, cards)

    planned: PlannedPlan = client.structured(PlannedPlan, prompt)
    steps = [
        make_step(
            s.instruction,
            requires_skill=s.requires_skill,
            required_tags=tuple(s.required_tags),
        )
        for s in planned.steps
    ]
    return Playbook(name=goal, steps=steps)
