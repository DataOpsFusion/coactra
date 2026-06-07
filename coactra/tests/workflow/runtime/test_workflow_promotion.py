import pytest

from coactra.workflow import (
    CandidateStatus,
    InMemoryProcedurePromotionStore,
    ReasoningTrace,
    Scope,
)


def _trace(*steps: str) -> ReasoningTrace:
    return ReasoningTrace(
        problem="deploy service",
        steps=[{"id": step, "kind": "task"} for step in steps],
    )


def test_procedure_candidate_requires_review_before_promotion_and_can_rollback():
    store = InMemoryProcedurePromotionStore()
    scope = Scope(tenant_id="acme")
    candidate = store.propose(_trace("build", "verify"), scope, proposed_by="agent:builder")

    with pytest.raises(ValueError, match="approved"):
        store.promote(candidate.id, scope, promoted_by="human:senior")

    approved = store.approve(candidate.id, scope, reviewed_by="human:senior")
    assert approved.status == CandidateStatus.approved
    v1 = store.promote(approved.id, scope, promoted_by="human:senior")
    assert v1.version == 1
    assert store.active("deploy service", scope).version == 1

    candidate2 = store.propose(
        _trace("build", "verify", "smoke-test"),
        scope,
        proposed_by="agent:builder",
    )
    store.approve(candidate2.id, scope, reviewed_by="human:senior")
    v2 = store.promote(candidate2.id, scope, promoted_by="human:senior")
    assert v2.version == 2

    rollback = store.rollback("deploy service", 1, scope, promoted_by="human:senior")
    assert rollback.version == 3
    assert rollback.rollback_of == 1
    assert [step.id for step in store.active("deploy service", scope).procedure.steps] == [
        "build",
        "verify",
    ]
