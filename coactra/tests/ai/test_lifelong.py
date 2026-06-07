from __future__ import annotations

from coactra.ai import (
    CurriculumTask,
    ExecutableSkill,
    InMemoryStore,
    LifelongLearner,
    SkillLibrary,
)
from coactra.ai.replay.engine import ReasoningEngine


def _embed(text: str) -> list[float]:
    return [1.0, float(len(text) % 7)]


def test_lifelong_learner_verifies_before_promoting_skill():
    store = InMemoryStore()
    reasoning = ReasoningEngine(store, _embed, reasoner=lambda problem: f"reason:{problem}")
    library = SkillLibrary()
    task = CurriculumTask(id="rotate", prompt="rotate cert", verifier="ok")

    def solver(task, library):
        return ExecutableSkill(
            id="cert.rotate",
            description="rotate certs",
            run=lambda env: f"ok:{env['service']}",
        )

    def verify(task, skill):
        return skill.run({"service": "api"}).startswith(task.verifier)

    learner = LifelongLearner(
        curriculum=[task],
        library=library,
        reasoning=reasoning,
        solve=solver,
        verify=verify,
    )

    result = learner.learn_next("acme")

    assert result.accepted is True
    assert result.skill_id == "cert.rotate"
    assert library.get("cert.rotate").run({"service": "api"}) == "ok:api"
    trace = store.get("acme", result.trace_id)
    assert trace.successes == 1
    assert trace.failures == 0


def test_lifelong_learner_rejects_failed_skill_and_records_feedback():
    store = InMemoryStore()
    reasoning = ReasoningEngine(store, _embed, reasoner=lambda problem: f"reason:{problem}")
    library = SkillLibrary()

    def solver(task, library):
        return ExecutableSkill(
            id="bad.skill",
            description="bad",
            run=lambda env: "nope",
        )

    learner = LifelongLearner(
        curriculum=[CurriculumTask(id="bad", prompt="do bad", verifier="ok")],
        library=library,
        reasoning=reasoning,
        solve=solver,
        verify=lambda task, skill: False,
    )

    result = learner.learn_next("acme")

    assert result.accepted is False
    assert library.get("bad.skill") is None
    trace = store.get("acme", result.trace_id)
    assert trace.successes == 0
    assert trace.failures == 1


def test_skill_library_composes_executable_skills_in_order():
    library = SkillLibrary()
    library.add(ExecutableSkill("first", run=lambda env: {**env, "a": 1}))
    library.add(ExecutableSkill("second", run=lambda env: {**env, "b": env["a"] + 1}))

    composed = library.compose("both", ["first", "second"])

    assert composed.run({}) == {"a": 1, "b": 2}
    assert library.get("both") is composed
