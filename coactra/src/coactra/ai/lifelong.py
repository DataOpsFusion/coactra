"""Small lifelong-learning coordinator over replay memory and executable skills.

This is deliberately honest: it is not an autonomous research agent.  It gives
hosts the Voyager-shaped loop as a library primitive: choose the next curriculum
task, solve it into an executable skill, verify that skill against environment
feedback, record the outcome, and promote only verified skills.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from coactra.ai.replay.engine import ReasoningEngine

__all__ = [
    "CurriculumTask",
    "ExecutableSkill",
    "LearningResult",
    "LifelongLearner",
    "SkillLibrary",
]


@dataclass(frozen=True)
class CurriculumTask:
    """One learnable environment task."""

    id: str
    prompt: str
    verifier: Any = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutableSkill:
    """A verified callable skill that can be replayed or composed."""

    id: str
    run: Callable[[dict[str, Any]], Any]
    description: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningResult:
    """Outcome of one curriculum attempt."""

    task_id: str
    skill_id: str
    trace_id: str
    accepted: bool
    output: Any = None


class SkillLibrary:
    """In-memory executable skill library with deterministic composition."""

    def __init__(self) -> None:
        self._skills: dict[str, ExecutableSkill] = {}

    def add(self, skill: ExecutableSkill) -> None:
        self._skills[skill.id] = skill

    def get(self, skill_id: str) -> ExecutableSkill | None:
        return self._skills.get(skill_id)

    def list(self) -> list[ExecutableSkill]:
        return list(self._skills.values())

    def compose(self, skill_id: str, steps: list[str], *, description: str = "") -> ExecutableSkill:
        missing = [name for name in steps if name not in self._skills]
        if missing:
            raise KeyError(", ".join(missing))

        def _run(env: dict[str, Any]) -> Any:
            state: Any = dict(env)
            for name in steps:
                state = self._skills[name].run(state if isinstance(state, dict) else {"input": state})
            return state

        skill = ExecutableSkill(
            id=skill_id,
            description=description or " -> ".join(steps),
            run=_run,
            meta={"composed_from": list(steps)},
        )
        self.add(skill)
        return skill


SolveFn = Callable[[CurriculumTask, SkillLibrary], ExecutableSkill]
VerifyFn = Callable[[CurriculumTask, ExecutableSkill], bool]


class LifelongLearner:
    """Curriculum -> solve -> self-verify -> promote loop.

    Solving and verification are host-provided because the library cannot know
    the environment.  The learner owns orchestration and feedback bookkeeping.
    """

    def __init__(
        self,
        *,
        curriculum: list[CurriculumTask],
        library: SkillLibrary,
        reasoning: ReasoningEngine,
        solve: SolveFn,
        verify: VerifyFn,
    ) -> None:
        self._curriculum = list(curriculum)
        self._library = library
        self._reasoning = reasoning
        self._solve = solve
        self._verify = verify
        self._completed: set[str] = set()

    def next_task(self) -> CurriculumTask | None:
        for task in self._curriculum:
            if task.id not in self._completed:
                return task
        return None

    def learn_next(self, tenant: str) -> LearningResult:
        task = self.next_task()
        if task is None:
            raise StopIteration("curriculum is complete")

        recall = self._reasoning.recall_or_reason(tenant, task.prompt)
        if recall.trace_id is None:
            trace_id = self._reasoning.capture(tenant, task.prompt, recall.answer)
        else:
            trace_id = recall.trace_id

        skill = self._solve(task, self._library)
        accepted = bool(self._verify(task, skill))
        self._reasoning.record_outcome(tenant, trace_id, accepted)
        if accepted:
            self._library.add(skill)
            self._completed.add(task.id)
        return LearningResult(
            task_id=task.id,
            skill_id=skill.id,
            trace_id=trace_id,
            accepted=accepted,
        )
