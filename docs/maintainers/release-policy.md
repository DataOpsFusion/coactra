# Release Policy

Coactra is currently at **alpha** (`0.0.x`). The alpha phase covers the Agent core
milestone. No backward-compatibility guarantees are made while the public surface
is being established. Each milestone (Agent → workspace → Team → Workflow) ships
as a minor version increment.

## Alpha Surface (0.0.x)

The removed layer (ports-based factory, ports-based Agent, sync collaboration stack)
has been deleted in the alpha redesign. Compatibility-only import shims are not
part of the alpha API; move implementation and tests to the current package names
instead of preserving old paths.

Public exports:

```python
from coactra import Agent, Decision, DecisionOutcome, Policy, PolicyRequest, RemotePeer, Scope, Skill, StaticToken, Team, Workflow
```

Anything not exported from `coactra` directly is internal and may change at any time.

`coactra.team` is facade-only in alpha: import directory/org/auth helpers from `coactra.team.directory`, not from `coactra.team`.

Advanced seams (not root exports):

- `coactra.team.directory` — **beta** org/member/seat persistence and authorization helpers
- `coactra.agent.adapters` — outbound A2A transport (`OfficialA2ATransport`), Keycloak token exchange
- Inbound A2A serving — use the official `a2a-sdk` server APIs directly
- OAuth client-credentials — use `authlib` or `httpx-oauth`; pass result to `auth=`

## Stability Tiers (target for v1)

| Tier | Meaning | Allowed changes |
|---|---|---|
| `stable` | Preferred public API | No breaking change without deprecation window |
| `beta` | Public but may change before v1 | Changes allowed with changelog + migration note |
| `experimental` | Useful but not compatibility-promised | May change between minor releases |
| `internal` | Implementation detail | Can change anytime |

## Preferred Import Root (v1 target)

```
from coactra import Agent, Decision, DecisionOutcome, Policy, PolicyRequest, RemotePeer, Scope, Skill, StaticToken, Team, Workflow
```

Use the top-level `coactra` imports for application code. Lower-level roots such as `coactra.workflow.ledger` and `coactra.team.directory` are implementation surfaces and may change during alpha. Do not reintroduce alias packages for removed roots.

## Adapter Maturity vs API Stability

An adapter can be import-stable but operationally experimental. Track both:

- **API stability** — can the constructor/import contract change?
- **Adapter maturity** — is the backend suitable for production?

## Runtime Resume Semantics

Every workflow engine adapter declares one of:

| Value | Meaning |
|---|---|
| `same-thread` | `resume(id, ...)` continues the same durable execution |
| `new-run-with-prior-state` | Resume starts a new run carrying previous state |
| `unsupported` | Adapter can start but cannot resume |
| `host-owned` | Coactra passes through; host code owns real resume behavior |

## Cleanup Status

See `design/IMPLEMENTATION_STATUS.md` for the current cleanup status.
