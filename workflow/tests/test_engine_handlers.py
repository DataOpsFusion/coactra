import pytest

from coactra.workflow import (
    EscalationUnresolved,
    LangGraphEngine,
    Procedure,
    RejectAll,
    RunContext,
    Scope,
    Step,
    TerminalHumanRouter,
)


def _ctx(**kw):
    base = dict(scope=Scope(tenant_id="acme"))
    base.update(kw)
    return RunContext(**base)


def test_approve_reject_stops_before_the_guarded_step():
    ran: list[str] = []
    eng = LangGraphEngine(tasks={"apply": lambda s: ran.append("apply") or s})
    proc = Procedure(
        name="gated",
        steps=[
            Step(id="gate", kind="approve", next="apply"),
            Step(id="apply", kind="task"),
        ],
    )
    result = eng.run(proc, {}, _ctx(approver=RejectAll()))
    assert ran == []  # rejected -> guarded step never ran
    assert "apply" not in result.path


def test_ask_carries_the_question_and_records_the_answer():
    asked: list[tuple[str, str]] = []

    class Recorder:
        def ask(self, agent, question, state):
            asked.append((agent, question))
            return "safe to ship"

    eng = LangGraphEngine(tasks={"done": lambda s: s})
    proc = Procedure(
        name="consult",
        steps=[
            Step(id="consult", kind="ask", agent="security", question="is this safe?", next="done"),
            Step(id="done", kind="task"),
        ],
    )
    result = eng.run(proc, {}, _ctx(collaborator=Recorder()))
    assert asked == [("security", "is this safe?")]  # the step's question reached the agent
    assert result.output["answers"]["security"] == "safe to ship"


def test_escalate_routes_to_terminal_decider():
    eng = LangGraphEngine()
    proc = Procedure(
        name="stuck",
        steps=[Step(id="bump", kind="escalate", reason="cannot decide")],
    )
    ctx = _ctx(router=TerminalHumanRouter(), chain=["manager", "director", "human"])
    result = eng.run(proc, {}, ctx)
    assert result.output["decider"] == "human"


def test_escalate_with_empty_chain_raises_unresolved():
    eng = LangGraphEngine()
    proc = Procedure(
        name="stuck",
        steps=[Step(id="bump", kind="escalate", reason="no chain")],
    )
    with pytest.raises(EscalationUnresolved):
        eng.run(proc, {}, _ctx(chain=[]))


def test_workflow_holds_no_org_logic():
    # The router decides who; workflow only hands it the opaque chain. Proven by the fact
    # that swapping the chain changes the decider with zero workflow code change.
    eng = LangGraphEngine()
    proc = Procedure(name="x", steps=[Step(id="e", kind="escalate")])
    a = eng.run(proc, {}, _ctx(chain=["human"]))
    b = eng.run(proc, {}, _ctx(chain=["sota"]))
    assert a.output["decider"] == "human"
    assert b.output["decider"] == "sota"
