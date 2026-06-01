import pytest

from fleetlib.workflow import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)


def test_default_approver_protocols_are_runtime_checkable():
    assert isinstance(AutoApprove(), Approver)
    assert isinstance(RejectAll(), Approver)
    assert isinstance(NullCollaborator(), Collaborator)
    assert isinstance(TerminalHumanRouter(), EscalationRouter)


def test_auto_approve_and_reject_all():
    assert AutoApprove().approve("deploy", {"x": 1}) is True
    assert RejectAll().approve("deploy", {"x": 1}) is False


def test_null_collaborator_echoes_a_recorded_answer():
    c = NullCollaborator(answers={"security": "looks fine"})
    assert c.ask("security", "is this safe?", {}) == "looks fine"


def test_terminal_human_router_resolves_at_the_human():
    router = TerminalHumanRouter()
    esc = Escalation(reason="cannot decide", state={"k": 1})
    decision = router.route(esc, chain=["manager", "human"])
    assert decision == "human"  # walked up to the terminal decider


def test_router_raises_when_chain_has_no_decider():
    router = TerminalHumanRouter()
    esc = Escalation(reason="stuck", state={})
    with pytest.raises(EscalationUnresolved):
        router.route(esc, chain=[])
