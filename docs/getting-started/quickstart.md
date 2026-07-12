# Quickstart

This guide builds a small incident-triage system using the Team-first public API. `Team` is the
assembly door; runtime agents are created through `team.add_agent(...)` and then routed through the
same Team policy and scope boundary.

## 1. Install

```bash
pip install "coactra[agent]"
```

For source development:

```bash
python -m pip install -e "./coactra[all,dev]"
```

## 2. Write A Tool

```python
def get_runbook(service: str) -> str:
    runbooks = {
        "nginx": "https://wiki.example.com/runbooks/nginx",
        "postgres": "https://wiki.example.com/runbooks/postgres",
    }
    return runbooks.get(service, "https://wiki.example.com/runbooks/generic")
```

## 3. Create A Team And Add An Agent

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team


def get_runbook(service: str) -> str:
    return f"https://wiki.example.com/runbooks/{service}"


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="triage",
                profile=ModelProfile(
                    name="triage",
                    model="openai/deepseek-v4-pro",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    agent = await team.add_agent(
        model_capability="triage",
        name="triage-agent",
        auth="dev-token",
        tools=[get_runbook],
        skills=[Skill(id="incident", description="Triage production incidents", tags=["triage"])],
        instructions="You are a senior SRE. Be concise and actionable.",
        expose=True,
    )
    answer = await agent.run("Triage nginx 502s on checkout")
    print(answer)


asyncio.run(main())
```

For deterministic local tests, route a capability to `TestModel()` or `FunctionModel(...)` instead of a live provider.

## 4. Add Memory, Workspace, Or Gateway Tools

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="ops"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="sre",
            profile=ModelProfile(
                name="sre",
                model="openai/deepseek-v4-pro",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="sre",
    name="sre-agent",
    gateway="https://gateway.example/mcp",
    auth=StaticToken("your-gateway-token"),
    memory="graphiti",
    workspace="./desk",
)
```

## 5. Route Across A Team

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="security"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="security-review",
            profile=ModelProfile(
                name="security-review",
                model="openai/deepseek-v4-pro",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
await team.add_agent(
    model_capability="security-review",
    name="security-reviewer",
    auth="dev-token",
    skills=[Skill(id="security", description="Review security-sensitive changes", tags=["review", "prod"])],
    expose=True,
)
await team.add_agent(
    model_capability="security-review",
    name="security-operator",
    auth="dev-token",
    skills=[Skill(id="security", description="Execute security changes", tags=["execute", "prod"])],
    expose=True,
)
print(team.match_skill("security", required_tags=["review"]).card)
```

Broad skill ids keep the roster portable. `required_tags` is the supported way to disambiguate overlapping specialists. `team.match_skill("security")` fails closed if the match is ambiguous.

## 6. Run A Workflow

```python
from coactra import Workflow
from coactra.workflow import ProofBundle, VerificationReceipt, step

workflow = Workflow(
    "cert rotation",
    steps=[
        step("plan the change", requires_skill="security", required_tags=["review"]),
        step("apply the rotation", requires_skill="security", required_tags=["execute"]),
        step("human sign-off", approve=True, approval_only=True),
    ],
)

run = await team.run(workflow)
if run.status == "interrupted":
    run = await workflow.resume(
        run,
        team,
        decision={
            "approved": True,
            "proof_bundle": ProofBundle(
                summary="review completed and operator approved",
                receipts=[
                    VerificationReceipt(
                        command="openssl s_client -connect example.com:443",
                        exit_code=0,
                        stdout_sha256="abc123",
                    )
                ],
            ),
        },
    )
```

`Workflow` supports Team skill routing, approval pause/resume with proof bundles, checkpoint storage, and swappable engine seams. For the common implement/verify/review pattern, see `coactra.agent.recipes.code_change(...)` in [Code Change Workflow](../examples/code-change-workflow.md).

## 7. Production Shape

| Concern | Development | Production |
|---|---|---|
| Policy | `Policy.permissive()` | guarded / approval-gated custom policy |
| Scope | `Scope(tenant_id="acme", namespace="support")` | tenant/workspace-qualified scope |
| Model | `TestModel()` / `FunctionModel(...)` route | Team-owned routed profiles via `ModelResolver` |
| Tools | local callables | `gateway=` plus scoped auth |
| Memory | in-process or named local backend | Graphiti/mem0 adapter with tenant scope |
| Workspace | local gated directory | host-controlled workspace backend |
| Peers | local runtime agents | `RemotePeer(...)` over A2A |

Coactra should give you stable seams. Keep business behavior in plain functions and let `Team` and `Workflow` own coordination, policy, and durable state.
