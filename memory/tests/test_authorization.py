import pytest

from coactra.memory import (
    AllowListMemoryAuthorizer,
    AuthorizedMemory,
    Memory,
    MemoryAccess,
    MemoryAccessDenied,
    Scope,
    make_backend,
)


@pytest.mark.asyncio
async def test_authorized_memory_enforces_exact_shared_scope_grants():
    department = Scope(tenant="acme", namespace="department/engineering")
    company = Scope(tenant="acme", namespace="company")
    policy = AllowListMemoryAuthorizer()
    policy.grant("agent:builder", MemoryAccess.write, department)
    policy.grant("agent:builder", MemoryAccess.read, department)
    memory = AuthorizedMemory(
        Memory(backend=make_backend("inprocess")),
        actor="agent:builder",
        authorizer=policy,
    )

    await memory.remember(["deploy procedure"], department)
    assert (await memory.recall("deploy", department))[0].text == "deploy procedure"

    with pytest.raises(MemoryAccessDenied):
        await memory.remember(["private"], company)
    with pytest.raises(MemoryAccessDenied):
        await memory.recall("deploy", company)
