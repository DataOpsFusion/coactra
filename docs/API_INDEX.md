# Public API Index

This page lists the symbols application code should import from Coactra package roots.
See [maintainers/release-policy.md](maintainers/release-policy.md) for stability tiers,
deprecation rules, and the review checklist.

Coactra ships as **one PyPI distribution** (`pip install coactra`). Capabilities and
backends are optional extras (`pip install "coactra[agent,sql]"`). There are no separate
`coactra-*` distributions.

## Stable V1 surface (preferred imports)

These roots are the intended long-lived application API. Until v1 they may still change,
but changes should be intentional, documented, and covered by tests.

```python
from coactra.scope import CoactraScope
from coactra.memory import Memory, make_backend
from coactra.jobs import WorkManager, WorkOrder
from coactra.workspace import open_workspace, Workspace
from coactra.agent import make_agent, Agent
from coactra.errors import CoactraError, ErrorCode, MissingExtraError
```

| Module | Stable symbols | Extra (if any) |
|---|---|---|
| `coactra.scope` | `CoactraScope`, `Scope` (alias), `is_safe_path_component` | — |
| `coactra.memory` | `Memory`, `make_backend`, `Scope`, `Recollection`, `MemoryBackend`, `AuthorizedMemory` | backends: `mem0`, `graphiti` |
| `coactra.jobs` | `WorkManager`, `WorkOrder`, `WorkScope`, `Scope` (alias), `Orchestrator`, `DurableOrchestrator`, `Procedure` | SQL: `sql`; workflow runtimes: `langgraph`, `temporal`, `prefect`, … |
| `coactra.workspace` | `open_workspace`, `Workspace`, `WorkspaceBackend`, `LocalFilesystemBackend`, `CliPolicy` | — |
| `coactra.agent` | `make_agent`, `Agent`, `Scope`, port Protocols (`AIPort`, `MemoryPort`, …), collaboration policy types | `agent`; integrations: `a2a`, `oauth` |
| `coactra.errors` | `CoactraError`, `ErrorCode`, `ErrorInfo`, `MissingExtraError`, `coactra_error_from_exception` | — |
| `coactra.ai` | `ask`, `structured`, `Client`, `ReasoningEngine`, `InMemoryStore` | `ai`; backends: `chroma`, `tiktoken` |
| `coactra.directory` | `Organization`, `OrgStore`, `make_org_store`, `Authorizer`, `CompanySpec`, `bootstrap_company` | `organization`; backends: `postgres`, `openfga` |

Each capability module also exposes a local `Scope` type (`coactra.memory.Scope`,
`coactra.workspace.Scope`, etc.). For apps composing multiple capabilities, prefer
`CoactraScope` and the `to_*_kwargs()` helpers.

## Beta (public, still settling)

These modules are documented and import-stable enough for early adopters, but their
contracts may change with a migration note before v1.

| Module | Symbols | Notes |
|---|---|---|
| `coactra.agent.integrations` | `make_coactra_agent`, wiring helpers | Composition helpers for production agent setup. |

## Experimental

Exploratory APIs and integration seams. May change or be removed without a deprecation
window. Do not build production examples that require these without accepting churn.

| Area | Import path | Examples |
|---|---|---|
| Workflow DSL and graph builders | `coactra.jobs.workflow` | `build_graph`, `run_workflow`, `Step`, `document_from_procedure` |
| Durable LangGraph engine | `coactra.jobs` | `DurableLangGraphEngine` |
| Alternate workflow adapters | `coactra.jobs.workflow.adapters` | Temporal, Prefect, DBOS engines |
| Workflow capability registry | `coactra.jobs` | `CapabilityRegistry`, `InMemoryCapabilityRegistry`, `CapabilityValidationError` |
| Agent SDK facade | `coactra.agent.sdk` | `Agent` (PydanticAI-oriented; deliberately omitted from `coactra.agent.__all__`) |
| Memory / workspace / jobs adapters | `*.adapters`, `*.backends` | Provider-specific wiring; import only at backend boundaries. |
| Function shell and task hooks | `coactra.kernel`, `coactra.plugins` | `Kernel`, `PluginManager`, and hook DTOs are not used by the main facades yet. |

Install workflow extras explicitly, for example `pip install "coactra[langgraph]"`.

## Compatibility (deprecated root lookups)

These symbols remain reachable for migration but emit `DeprecationWarning` when accessed
from `coactra.agent` root:

- `FakeAI`, `FakeMemory`, `FakeWorkspace`, `FakeWorkflow`, `FakeOrganization`, `FakeWork`
- `ToolTrie`, A2A server helpers (`build_a2a_app`, …)

Prefer concrete submodule imports, for example `from coactra.agent.ports import FakeAI`.

Legacy package shims (`coactra.orchestration`, `coactra.work`, `coactra.workflow`,
`coactra.organization`) remain importable. See [concepts/naming-migration.md](concepts/naming-migration.md).

## Internal (do not import in application code)

Implementation modules, private adapters, conformance test helpers, and re-exported
work submodules loaded by `coactra.jobs` for compatibility. These may change without notice:

- `coactra.jobs.work.*` subpackages re-exported at `coactra.jobs.*` (store, service, routing, …)
- `coactra.*._optional`, `coactra.*._stub`, `coactra.*._errors`
- `coactra.agent.domain` internals beyond the public `Scope` / `ToolSpec` surface
- Test-only fakes outside documented adapter boundaries

## Install quick reference

```bash
pip install coactra                    # core + jobs/work (WorkManager)
pip install "coactra[agent]"           # agent facade
pip install "coactra[ai]"              # LiteLLM / Instructor shelf
pip install "coactra[memory]"          # memory facade (backends optional)
pip install "coactra[organization]"    # directory / org model
pip install "coactra[sql]"             # SqlWorkStore
pip install "coactra[langgraph]"       # default workflow runtime
pip install "coactra[all,dev]"         # all capability extras + pytest (from source)
```

## Related docs

- [Interface map](concepts/interfaces.md): how the stable roots fit together.
- [Library map](concepts/library-map.md): capability boundaries and philosophy.
- [Release policy](maintainers/release-policy.md): versioning, tiers, and publishing.
