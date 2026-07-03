import pytest
from pydantic import ValidationError

from coactra.workflow import Procedure, RunResult, Step


def test_task_step_minimal():
    s = Step(id="deploy", kind="task")
    assert s.kind == "task"
    assert s.id == "deploy"
    assert s.next is None


def test_branch_step_requires_condition_and_targets():
    s = Step(
        id="check",
        kind="branch",
        condition="ok",  # flat state key — the LangGraphEngine selector does state.get("ok")
        if_true="done",
        if_false="rollback",
    )
    assert s.if_true == "done"
    assert s.if_false == "rollback"


def test_branch_without_condition_is_rejected():
    with pytest.raises(ValidationError):
        Step(id="check", kind="branch", if_true="a", if_false="b")


def test_ask_step_carries_target_agent_and_question():
    s = Step(id="consult", kind="ask", agent="security", question="is this safe?", next="apply")
    assert s.agent == "security"
    assert s.question == "is this safe?"


def test_procedure_is_ordered_and_indexed_by_id():
    p = Procedure(
        name="deploy-flow",
        steps=[Step(id="a", kind="task", next="b"), Step(id="b", kind="task")],
    )
    assert [s.id for s in p.steps] == ["a", "b"]
    assert p.step("b").id == "b"
    assert p.entry.id == "a"


def test_run_result_holds_path_and_output():
    r = RunResult(output={"ok": True}, path=["a", "b"])
    assert r.output == {"ok": True}
    assert r.path == ["a", "b"]


def test_step_reports_explicit_targets() -> None:
    step = Step(
        id="route", kind="branch", condition="ok", if_true="yes", if_false="no", next="done"
    )

    assert step.target_ids() == ("done", "yes", "no")


def test_procedure_rejects_duplicate_step_ids() -> None:
    with pytest.raises(ValueError, match="duplicate workflow step ids"):
        Procedure(
            name="bad",
            steps=[
                Step(id="same", kind="task"),
                Step(id="same", kind="task"),
            ],
        )


def test_procedure_rejects_unknown_next_target() -> None:
    with pytest.raises(ValueError, match="unknown targets"):
        Procedure(name="bad", steps=[Step(id="start", kind="task", next="missing")])


def test_procedure_rejects_unknown_branch_target() -> None:
    with pytest.raises(ValueError, match="route->missing"):
        Procedure(
            name="bad",
            steps=[
                Step(id="route", kind="branch", condition="ok", if_true="done", if_false="missing"),
                Step(id="done", kind="task"),
            ],
        )
