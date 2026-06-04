# Adapter Maturity

Use this file before recommending an adapter for production. A named adapter is not automatically production-ready.

## Maturity Labels

- `reference`: implemented default suitable for tests, demos, or limited production when its storage model fits.
- `implemented`: functional adapter; production readiness depends on host configuration and external service hardening.
- `experimental`: useful bridge with unstable assumptions or limited production proof.
- `stub`: named seam only; raises or is intentionally incomplete.
- `compatibility`: old import path or alias for migration.

## Current Matrix

| Package | Adapter / backend | Maturity | Notes |
|---|---|---|---|
| `coactra-ai` | `LiteLLM` completion client | implemented | Main model-call wrapper through LiteLLM/Instructor. |
| `coactra-ai` | `ChromaStore` | implemented | Optional vector trace store, depends on Chroma. |
| `coactra-memory` | `InProcessBackend` | reference | Offline lexical memory, process-local. |
| `coactra-memory` | `Mem0Backend` | implemented | Wraps sync mem0 behind async protocol. |
| `coactra-memory` | `GraphitiBackend` | implemented | Requires Graphiti/Neo4j and model/embed clients. Export is approximate/lossy. |
| `coactra-workspace` | `LocalFilesystemBackend` | reference | File confinement implemented. Exec disabled by default. |
| `coactra-workspace` | `DaytonaBackend` | stub | Seam only. |
| `coactra-workspace` | `E2BBackend` | stub | Seam only. |
| `coactra-workspace` | `OpenHandsBackend` | stub | Seam only. |
| `coactra-orchestration.work` | `InMemoryWorkStore` | reference | Process-local work ledger for tests/demos. |
| `coactra-orchestration.work` | `SqlWorkStore` | implemented | Durable SQL ledger with optimistic concurrency. |
| `coactra-orchestration.work` | `DBOSDispatcher` | experimental | Thin dispatch bridge; Coactra ledger remains source of truth. |
| `coactra-orchestration.work` | `TemporalDispatcher` | experimental | Thin dispatch bridge; not a full workflow backend. |
| `coactra-orchestration.work` | `DaprDispatcher` | experimental | Thin dispatch bridge. |
| `coactra-orchestration.work` | `MCPTasksAdapter` | experimental | MCP task shape bridge. |
| `coactra-orchestration.workflow` | `LangGraphEngine` | implemented | Optional LangGraph procedure runner. |
| `coactra-orchestration.workflow` | `DurableLangGraphEngine` | implemented | Official default durable workflow adapter when `coactra-orchestration[langgraph]` is installed; restart contract must be explicit. |
| `coactra-orchestration.workflow` | `TemporalEngine` | implemented | Thin `WorkflowEngine` adapter over a host Temporal client/workflow/task queue; same-thread resume via workflow signal. |
| `coactra-orchestration.workflow` | `PrefectEngine` | implemented | Thin deployment-run adapter; resume starts a new run carrying prior thread state and decision payload. |
| `coactra-organization` | `SqliteOrgStore` | reference | SQLModel/SQLAlchemy repository. |
| `coactra-organization` | `AsyncPostgresOrgStore` | implemented | Async facade over SQL repository using worker-thread offload. |
| `coactra-organization` | `OpenFGAAuthorizer` | implemented | Authorization seam over OpenFGA SDK. |
| `coactra-organization` | `Neo4jOrgStore` | stub | Seam only. |
| `coactra-agent` | `InProcessExchanger` | reference | Local no-passthrough token exchanger for tests/demos. |
| `coactra-agent` | `KeycloakExchanger` | implemented | RFC 8693 token exchange over configured token endpoint. |
| `coactra-agent` | `OfficialA2ATransport` | implemented | Outbound official A2A SDK adapter. |
| `coactra-agent` | inbound A2A helpers | implemented | Requires verifier for production use. |
| `coactra-agent` | `FastMCPServer` | stub | Seam only. |

## Runtime Resume Semantics

Runtime adapters must document one of these values before they are recommended for production:

| Value | Meaning |
|---|---|
| `same-thread` | `resume(thread_id, ...)` continues the same external durable execution. |
| `new-run-with-prior-state` | resume starts a new external run that carries prior state and the decision payload. |
| `unsupported` | adapter can start work but cannot resume. |
| `host-owned` | Coactra invokes the adapter, but host workflow code owns the real pause/resume behavior. |

Current target expectation:

- `DurableLangGraphEngine`: same-thread when configured with a persistent checkpointer and stable thread id.
- `TemporalEngine`: same-thread via workflow id and signal.
- `PrefectEngine`: new-run-with-prior-state; host flow code owns true replay or resume behavior.

## Production Rule

A production stack should prefer:

- `SqlWorkStore` over `InMemoryWorkStore`
- sandbox-backed workspace over unsafe local exec
- real memory backend over in-process memory when memory must survive restart
- real token exchange over in-process exchanger
- required A2A verifier on inbound services
- explicit adapter maturity checks before deployment
