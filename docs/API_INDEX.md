# API Index

Complete public surface for Coactra 0.x (alpha). Tags: **Available** = works today; **Advanced seam** = available but requires host wiring or optional runtime adapters.

## Top-Level Exports

```python
from coactra import (
    Agent, AgentSpec, CoactraError, Decision, DecisionOutcome, ErrorCode,
    MissingExtraError, ModelProfile, ModelResolver, ModelRoute,
    Policy, PolicyRequest, RemotePeer, Run, Scope, Skill,
    StaticToken, Team, ValidationError, Workflow, __version__,
)
```

| Name | Type | Status | Description |
|------|------|--------|-------------|
| `Agent` | class | **Available** | Thin facade over pydantic-ai: model, tools, memory, workspace, skills, and peers. |
| `AgentSpec` | dataclass | **Available** | Canonical declarative composition of one agent: identity, model routing, scope, skills, tools, memory, and runtime config. |
| `RemotePeer` | dataclass | **Available** | Remote A2A peer config for outbound delegation tools. |
| `Run` | class | **Available** | Handle returned by `agent.send(...)`; supports `stream()` and `wait()`. |
| `Decision` | dataclass | **Available** | Shared policy decision payload with outcome, reason, source, and metadata. |
| `DecisionOutcome` | enum | **Available** | Shared policy outcomes: `allow`, `deny`, `requires_approval`. |
| `Policy` | protocol | **Available** | Cross-cutting policy contract for governed actions across components. |
| `PolicyRequest` | dataclass | **Available** | Shared policy input payload: principal, action, resource, scope, component, and context. |
| `ModelProfile` | dataclass | **Available** | Declarative model profile metadata used by governed routing. |
| `ModelResolver` | class | **Available** | Policy-gated resolver from model capability to a concrete route. |
| `ModelRoute` | dataclass | **Available** | Mapping from a capability name to model/provider/runtime defaults. |
| `Scope` | dataclass | **Available** | Canonical composed-app scope DTO (`tenant_id`, `namespace`, `agent_id`, `session_id`). |
| `Skill` | dataclass | **Available** | Structured skill entry for the Agent Card. |
| `StaticToken` | class | **Available** | Pre-fetched JWT token source for dev / CI. |
| `Team` | class | **Available** | Team-first coordination root with explicit scope, policy, catalogs, routing, and execution. |
| `Workflow` | class | **Available** | Playbook runner with capability routing, approvals, checkpoint resume, and engine bridge. |
| `CoactraError` | class | **Available** | Base exception for all Coactra errors. |
| `ErrorCode` | enum | **Available** | Machine-readable error categories (TIMEOUT, VALIDATION, PROVIDER, etc.). |
| `MissingExtraError` | class | **Available** | Raised when an optional extra is required but not installed. |
| `ValidationError` | class | **Available** | Input or contract validation failed. |
| `__version__` | str | **Available** | Installed distribution version. |

## Public API Contract

The application-facing contract is intentionally small: start from the root `coactra` exports above. Lower-level modules such as `coactra.agent`, `coactra.workflow`, `coactra.workflow.ledger`, `coactra.memory`, and `coactra.workspace` are supported seams for adapters, persistence, events, and host runtime wiring. They are not the preferred first import path for application code.

`from coactra import Team` is the stable roster API. Deep imports from `coactra.team.directory` (org stores, authorization, bootstrap helpers) are **beta** — useful for host wiring but not compatibility-promised at v1.

`coactra.team` now exposes the public `Team` facade only. Directory control-plane APIs such as `Organization`, `OrgStore`, and `OpenFGAAuthorizer` remain available from `coactra.team.directory` as beta seams.

For OAuth client-credentials token fetch/refresh, use `authlib` or `httpx-oauth` and pass the result to `auth=` via `StaticToken` or a custom `TokenSource`. For inbound A2A serving, use the official `a2a-sdk` server APIs directly; the agent handler is `await agent.run(message)`. See [Bring Your Own Stack](getting-started/bring-your-own.md) for full recipes.

Removed alpha roots are intentionally not compatibility-shimmed; the exact banned names are enforced by the architecture guard and release checklist.

## External Install Functions

```python
from coactra import Skill, Team


def install_hermes(team: Team) -> None:
    team.add_skill(Skill("code.review", description="Review code changes"))
    # Real packages may also call team.add_agent(...), add model routes,
    # register workflows, or configure MCP/A2A adapters.


install_hermes(team)
```

Add a formal plugin API only after multiple real integrations need the same contract.

## Team.add_agent(...)

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, StaticToken, Team

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
    name="sre-1",
    gateway="https://gateway/mcp",
    auth=StaticToken("dev-token"),
    tools=[my_func],
    memory="graphiti",
    workspace="./desk",
    skills=[Skill(id="security", description="...", tags=["review", "tls"], scopes=["cert:write"])],
    peers=["security-agent"],
    expose=True,
    instructions="Be terse.",
    tracer=tracer,
)
```

`Team.add_agent(...)` is the public construction door. `model_capability=` is the governed route-selection path.

The same construction as an explicit spec — `AgentSpec` is the canonical form; the
keyword arguments above are convenience sugar over it:

```python
from coactra import AgentSpec, Skill

agent = await team.add_agent(
    AgentSpec(
        name="security-agent",
        model_capability="sre",
        instructions="You handle certificate rotation.",
        skills=[Skill(id="security", description="...", tags=["review", "tls"])],
    )
)
```

## run / send / stream

`agent.run(message, output=...)` returns text by default or a typed output object when `output=` is set.

`agent.send(message)` returns a `Run` handle. Call `.stream()` to iterate events or `.wait()` to await the final result.

```python
run = await agent.send("Investigate the latency spike.")
async for event in run.stream():
    ...
result = await run.wait()
```

Stream events are frozen dataclasses with `run_id` and `seq`: `Assistant`, `Thinking`, `ToolCall`, `ToolResult`, `Usage`, and terminal `Status`.

## Agent Card And Delegation

```python
card = agent.card
```

`agent.card` contains curated `name`, `tenant`, `skills`, and `securitySchemes`. Raw tool names, arguments, tokens, and credentials are never published. Outbound delegation is configured with `peers=`. For inbound A2A serving, wire the official `a2a-sdk` server and call `await agent.run(message)` in your handler.

## RemotePeer(...)

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, RemotePeer, Scope, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="delegation"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="delegation",
            profile=ModelProfile(
                name="delegation",
                model="openai/deepseek-v4-pro",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="delegation",
    name="sre-agent",
    peers=[RemotePeer(
        name="security-agent",
        endpoint="https://security.example/a2a",
        audience="security-agent",
    )],
)
```

`RemotePeer` creates an `ask_<name>` tool backed by the official A2A transport (`coactra.agent.adapters.OfficialA2ATransport`). Policy is checked before the wire is touched. A plain string peer is accepted for the documented `peers=["name"]` shape, but without a registry or remote config it reports unavailable.

## Skill(...)

```python
Skill(
    id="security",
    description="Review or operate TLS changes for acme.example domains.",
    tags=["review", "tls"],
    scopes=["cert:write"],
)
```

A plain string is also accepted anywhere `Skill` is: `skills=["security"]`.

## Scope(...)

```python
from coactra import Scope

scope = Scope(
    tenant_id="acme",
    namespace="support",
    agent_id="triage",
    session_id="session-1",
)
```

`Scope` is the canonical type across agent, memory, workspace, workflow, and ledger APIs. Import it from `coactra` (package roots re-export the same class) and pass the complete scope through each boundary.

## MCPServer(...) and workflow steps

Additive external MCP servers (not the primary `gateway=` path):

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team
from coactra.agent import MCPServer

team = Team(
    scope=Scope(tenant_id="acme", namespace="tools"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="tool-agent",
            profile=ModelProfile(
                name="tool-agent",
                model="openai/deepseek-v4-pro",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="tool-agent",
    name="tool-agent",
    tools=[MCPServer(url="https://tools.example/mcp", name="extra")],
)
```

Workflow playbook steps:

```python
from coactra.workflow import PlaybookStep, ProofBundle, VerificationReceipt, step

wf = Workflow("release", steps=[
    step("Run checks", requires_skill="deploy", required_tags=["execute"]),
    PlaybookStep(instruction="Human sign-off", approve=True, approval_only=True),
])

run = await team.run(wf)
if run.status == "interrupted":
    run = await wf.resume(
        run,
        team,
        decision={
            "approved": True,
            "proof_bundle": ProofBundle(
                summary="release checks passed",
                receipts=[
                    VerificationReceipt(command="make test", exit_code=0, stdout_sha256="abc123")
                ],
            ),
        },
    )
```

`required_tags` disambiguates broad skill ids. Approved steps require a `ProofBundle`, and `approval_only=True` marks a pure human gate. `coactra.workflow.Step` is a separate graph-node type for durable procedure engines.

Thin code-change helper (beta seam during alpha):

```python
from coactra.agent.recipes import CodeChangeRiskTier, VerificationCheck, VerifierRole, code_change

plan = code_change(
    "checkout-fix",
    implement_instruction="Patch checkout to reject invalid coupon signatures.",
    implement_skill="python",
    verifier_roles=[
        VerifierRole(
            role="functional",
            skill="python",
            required_tags=["verify"],
            checks=[
                VerificationCheck(
                    id="pytest",
                    kind="command",
                    instruction="Run the checkout unit tests.",
                )
            ],
        )
    ],
    review_skill="security",
    review_tags=["review"],
    risk_tier=CodeChangeRiskTier.high,
)
```

The helper returns a `CodeChangeWorkflowPlan`; execute `plan.workflow` like any other Workflow.

## Outbound A2A Adapters

```python
from coactra.agent.adapters import OfficialA2ATransport, OfficialA2AClient
```

Minimal outbound transport over the official `a2a-sdk`. For inbound serving, use `a2a-sdk` server APIs directly.

## Event Module

```python
from coactra.agent import (
    Agent, Run, RunResult,
    Assistant, Thinking, ToolCall, ToolResult, Usage, Status,
    Event,
)
```

Application code should prefer root imports for the main nouns (`Agent`, `Team`, `Workflow`, `Skill`, `RemotePeer`) and `coactra.agent` for lower-level event/runtime types.

## Errors

`coactra.errors` defines the error taxonomy. All coactra errors extend `CoactraError` and carry an `ErrorCode` and a `retryable` hint. Streamed failures surface as terminal `Status(state="error")` events and `RunResult.failed(...)` when a streamed run is awaited.
