# Interface Map

This page names the public surfaces application code should use. The rule is simple: import from package roots for core behavior, and from `.adapters` packages only when you are wiring an external system.

Start with [Quickstart](../getting-started/quickstart.md) if you are building your first app, then use the [example catalog](../getting-started/examples.md) to choose a sample close to your use case.

## Package Roots

| Need | Import from | Main objects |
|---|---|---|
| Shared scope conversion | `coactra.scope` | `CoactraScope` |
| Function-first task shell | `coactra.kernel` | `Kernel`, `Session`, `Task`, `TaskResult` |
| Task lifecycle hooks | `coactra.plugins` | `Plugin`, `PluginManager`, `HookContext` |
| Shared error contract | `coactra.errors` | `CoactraError`, `ErrorCode` |
| Model calls and reasoning reuse | `coactra.ai` | `ask`, `structured`, `Client`, `ReasoningEngine` |
| Long-term memory | `coactra.memory` | `Memory`, `MemoryBackend`, `make_backend`, `AuthorizedMemory` |
| Persistent workspace | `coactra.workspace` | `Workspace`, `open_workspace`, `WorkspaceBackend`, `CliPolicy` |
| Procedures and durable work | `coactra.jobs` | `Orchestrator`, `DurableOrchestrator`, `Procedure`, `WorkManager` |
| Work-order lifecycle | `coactra.jobs` | `WorkOrder`, `WorkManager`, `WorkStore`, `AtomicWorkStore`, `SqlWorkStore` |
| Tenant directory and authority | `coactra.directory` | `Organization`, `OrgStore`, `Authorizer`, `CompanySpec` |
| Runtime composition | `coactra.agent` | `Agent`, `make_agent`, ports, identity, collaboration policy |

## Naming Boundary

Use `coactra.jobs` for durable jobs, procedures, approvals, retries, and status.
Use `coactra.workspace` for files, handoff notes, command execution, and the persistent agent desk.
Use `coactra.directory` for tenants, members, roles, permissions, and escalation targets.


## Normal Application Shape

A normal app should not start with inheritance. Start with functions and inject the small Coactra object they need.

```python
from coactra.agent import Scope, make_agent


def answer_support_question(question: str) -> str:
    agent = make_agent(scope=Scope(tenant_id="acme", namespace="agent:support"))
    return agent.think(question)
```

When work must be durable, add `WorkManager`:

```python
from coactra.jobs import Scope, WorkManager, WorkOrder

work = WorkManager()
scope = Scope(tenant_id="acme", namespace="support")
order = work.submit(WorkOrder(scope=scope, title="Triage incident"))
```

When you want a small session shell around plain functions, use `Kernel`:

```python
from coactra.kernel import Kernel, Task
from coactra.scope import CoactraScope


def triage(context, task):
    return {"tenant": context.scope.tenant_id, "incident": task.input["incident"]}


kernel = Kernel.builder().with_handler("triage", triage).build()
session = kernel.session(CoactraScope(tenant_id="acme", namespace="support"))
result = await session.run(Task("triage", {"incident": "db-latency"}))
```

## Scope

Each package keeps a small local `Scope` so it can be installed independently. For a composed app, use `CoactraScope` as the canonical DTO and convert at the boundary.

```python
from coactra.scope import CoactraScope

scope = CoactraScope(
    tenant_id="acme",
    namespace="support",
    agent_id="triage-agent",
    session_id="session-1",
)

agent_kwargs = scope.to_agent_kwargs()
work_kwargs = scope.to_work_kwargs()
memory_kwargs = scope.to_memory_kwargs()
```

## A2A Placement

A2A is not a separate Coactra core package. It is transport plumbing for multi-agent services.

Use it only when one deployed agent service must call another deployed agent service.

| Layer | Owns |
|---|---|
| `coactra.agent` | `CollaborationPolicy`, `AllowSameTenant`, `PolicyGatedCollaborator`, `AsyncPolicyGatedCollaborator`, `A2ATransportPort`, `AsyncA2ATransportPort` |
| `coactra.agent.adapters` | `OfficialA2ATransport`, `build_a2a_app`, `A2AInboundRequest` |
| `coactra.jobs.adapters` | `to_a2a_agent_card`, `to_a2a_skill`, `to_a2a_artifact` |

Outbound async A2A host:

```python
from coactra.agent import AllowSameTenant, AsyncPolicyGatedCollaborator, Scope
from coactra.agent.adapters import OfficialA2ATransport

scope = Scope(tenant_id="acme", namespace="agent:triage")
transport = OfficialA2ATransport(
    endpoint_for=lambda ref: f"https://{ref.agent_id}.internal/a2a",
    audience_for=lambda ref: f"a2a://{ref.agent_id}",
    token_provider=issue_token,
)
collaborator = AsyncPolicyGatedCollaborator(
    transport=transport,
    policy=AllowSameTenant(),
    scope=scope,
    me="agent:triage",
)
reply = await collaborator.ask("agent:research", "Check the incident notes", {})
```

Inbound A2A server:

```python
from coactra.agent.adapters import A2AInboundRequest, build_a2a_app

async def handle(request: A2AInboundRequest) -> str:
    return await run_capability(request.requested_capability, request.params)

app = build_a2a_app(agent_card=agent_card, handler=handle, verifier=verifier)
```

The official A2A SDK path is async. The default `make_agent(...)` path is sync because it also supports workflow run contexts. Use `AsyncPolicyGatedCollaborator` directly for async A2A services.

## Examples

- [Example catalog](../getting-started/examples.md): choose the right runnable sample.
- [Basic incident triage](../examples/basic-incident-triage.md): smallest normal app using `make_agent` and `WorkManager`.
- [Composed support agent](../examples/composed-support-agent.md): richer port injection without subclassing.
- [Sample projects](../examples/index.md): memory, durable work, workspace, and multi-agent policy.
