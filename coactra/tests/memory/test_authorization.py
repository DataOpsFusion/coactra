import pytest

from coactra import Policy, PolicyRequest
from coactra.memory import AuthorizedMemory, Memory, MemoryAccessDenied, Scope, make_backend
from coactra.policy import Decision, DecisionOutcome


class ScopedMemoryPolicy:
    def __init__(self, allowed_scope: Scope) -> None:
        self._allowed_scope = allowed_scope

    async def check(self, request: PolicyRequest) -> Decision:
        allowed = request.resource == f"memory:{self._allowed_scope.key}"
        return Decision(
            outcome=DecisionOutcome.allow if allowed else DecisionOutcome.deny,
            source="test",
        )


@pytest.mark.asyncio
async def test_authorized_memory_enforces_policy_for_exact_scope():
    department = Scope(tenant_id="acme", namespace="department/engineering")
    company = Scope(tenant_id="acme", namespace="company")
    memory = AuthorizedMemory(
        Memory(backend=make_backend("inprocess")),
        actor="agent:builder",
        policy=ScopedMemoryPolicy(department),
    )

    await memory.remember(["deploy procedure"], department)
    assert (await memory.recall("deploy", department))[0].text == "deploy procedure"

    with pytest.raises(MemoryAccessDenied):
        await memory.remember(["private"], company)
    with pytest.raises(MemoryAccessDenied):
        await memory.recall("deploy", company)


@pytest.mark.asyncio
async def test_authorized_memory_honors_core_policy_outcomes():
    department = Scope(tenant_id="acme", namespace="department/engineering")
    allowed = AuthorizedMemory(
        Memory(backend=make_backend("inprocess")),
        actor="agent:builder",
        policy=Policy.permissive(),
    )
    denied = AuthorizedMemory(
        Memory(backend=make_backend("inprocess")),
        actor="agent:builder",
        policy=Policy.default_deny(),
    )

    await allowed.remember(["ok"], department)
    assert (await allowed.recall("ok", department))[0].text == "ok"
    with pytest.raises(MemoryAccessDenied):
        await denied.recall("ok", department)
