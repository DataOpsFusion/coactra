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


def test_authored_and_induced_are_the_same_type():
    authored = Procedure(name="x", steps=[Step(id="a", kind="task")])
    induced = Procedure(name="x", steps=[Step(id="a", kind="task")], is_induced=True)
    assert type(authored) is type(induced)
    assert authored.is_induced is False
    assert induced.is_induced is True


def test_run_result_holds_path_and_output():
    r = RunResult(output={"ok": True}, path=["a", "b"])
    assert r.output == {"ok": True}
    assert r.path == ["a", "b"]
