# Whole Project Design Audit

Date: 2026-07-02

Status update:

- Fixed: MCP memory recall now checks read ACLs when an ACL/actor is supplied.
- Fixed: workspace journal distillation rejects symlink/path escapes before sending
  file contents to an LLM.
- Improved: durable workflow tool invokers can receive actor/scope/runtime context
  through `ToolContext` when they accept a `context=` keyword.
- Completed: code-change workflow types moved to `coactra.agent.recipes` and
  LangGraph document compiler helpers are no longer exported from `coactra.workflow`.

This audit treats Coactra as a policy-aware composition library for AI workloads,
not as a single app framework. A host may run one agent, many agents, or attach
Coactra to existing automation; the common need is scoped, auditable wiring
through MCP/A2A without forcing users to rebuild their data or adopt one runtime.

## Applied Fixes

- MCP-backed memory recall now checks read authorization before reading bound
  scopes.
- Directory-backed `MemoryAcl` now models read and write grants separately.
- Journal distillation now rejects symlink/path escapes before reading journal
  entries into an LLM prompt.
- Durable workflow tool invokers can receive actor/scope/policy runtime context
  without breaking existing invokers that do not accept it.

## Executive Verdict

Coactra's strongest shape is a control-plane library:

- Own: `Scope`, `Policy`, `Team`, identity/token exchange, resource access, work
  ledger, approval/audit vocabulary, and thin adapter contracts.
- Delegate: model loops, graph execution, RAG engines, memory ranking,
  scheduling, worker durability, retries, and wire-protocol servers.

That matches the industry direction. MCP defines a standard for connecting AI
applications to tools/resources/prompts, but explicitly does not dictate how an AI app
uses models or manages context. A2A is complementary: MCP is for tools/resources,
A2A is for agents delegating work to other agents. Popular frameworks such as
Pydantic AI, LangGraph, CrewAI, LlamaIndex, and AutoGen already cover agent loops,
multi-agent orchestration, RAG/data connectors, and runtime graphs. Coactra should
not compete with all of them. It should make them governable, composable, scoped,
and auditable.

## Philosophy

The library should say:

> Bring your own model runtime, memory store, tools, protocols, and workflow engine.
> Coactra wires them into scoped, policy-aware application flows.

That is a better thesis than "a new agent framework." It keeps the public API smaller
and makes adoption easier for host applications and users who already have
data in Graphiti, mem0, vector stores, SQL, document stores, MCP servers, or custom
internal systems.

## Highest Priority Findings

### 1. `Workflow` Is Carrying Too Many Concepts

Root `coactra.Workflow` resolves to `coactra.agent.workflow`, while
`coactra.workflow` exports durable runtimes, stores, handlers, routing, promotion,
and ledger names. The `Workflow` class also mixes playbook execution, durable engine
bridging, checkpoint resume, planner triage, and a code-change helper.

Impact:

- Low locality: unrelated workflow concerns feel like one public object.
- Harder to explain: users cannot tell whether Workflow means a playbook, durable
  engine, ledger run, or code-change recipe.
- Higher maintenance cost: every workflow improvement risks public API churn.

Recommendation:

- Pick one public fleet workflow interface. Prefer `Workflow` as the authored
  playbook UX because it is easy to read.
- Keep `WorkflowEngine` as the durable runtime SPI.
- Make `Procedure` an internal/intermediate representation or move it to an
  advanced namespace.
- Done: moved `Workflow.code_change(...)` and code-change-specific types into
  `coactra.agent.recipes.code_change(...)`.
- Done: LangGraph document compiler helpers such as `build_graph`, `run_workflow`,
  `document_from_procedure`, and done-criteria helpers are adapter-only imports;
  they are no longer exported from the public `coactra.workflow` namespace.

Concrete files:

- `coactra/src/coactra/__init__.py`
- `coactra/src/coactra/agent/workflow.py`
- `coactra/src/coactra/workflow/__init__.py`
- `coactra/src/coactra/workflow/backends/durable_langgraph.py`

### 2. `Team.add_agent` Is Too Wide

`Team.add_agent` exposes model routing, gateway auth, runtime, tools, memory,
workspace, skills, peer registry, learned procedures, procedure engine, tracing, and
defaults in one method. Internally it duplicates much of `_AgentSpec` and forwards the
same shape into `build_agent`.

Impact:

- The main assembly seam is shallow: callers must learn all components at once.
- Adding flexibility means adding more kwargs.
- The public API feels strict and broad at the same time.

Recommendation:

- Promote a real public `AgentSpec`/`AgentConfig` input object if it replaces the
  wide method shape rather than adding another parallel path.
- Keep `Team.add_agent(name=..., **simple_parts)` as low ceremony, but let advanced
  callers pass `spec=AgentSpec(...)`.
- Centralize normalizers:
  - `normalize_runtime`
  - `normalize_memory`
  - `normalize_workspace`
  - `normalize_tools`
  - `normalize_peers`
  - `normalize_skills`

This gives users flexible components without making every caller implement adapters.

Concrete files:

- `coactra/src/coactra/team/facade.py`
- `coactra/src/coactra/agent/facade.py`
- `coactra/src/coactra/agent/bindings.py`
- `coactra/src/coactra/agent/runtime_wiring.py`

### 3. Policy Is Not Present at Every Resource Seam

There are real security gaps caused by inconsistent policy locality:

- MCP memory recall checks no ACL before reading bound aliases. `publish_memory`
  checks writes, but `recall_facts` can read shared aliases if they are bound.
- Journal distillation accepts an arbitrary `Path` and reads files directly instead
  of going through a confined workspace backend or reader.
- Durable workflow tool invocation has no principal/scope/policy context in
  `ToolInvoker.call(...)`.
- `Team.local()` defaults to permissive policy. That is fine for demos, but risky as
  the public assembly root for a fleet.

Recommendation:

- Make policy context part of resource/tool seams, not something every adapter must
  remember.
- Require read checks and write checks for memory-backed MCP tools.
- Change journal distillation to accept `Workspace + relative journal path` or a
  constrained reader callable.
- Extend durable tool invocation with actor/scope/context, or wrap invokers in a
  policy-aware adapter.
- Consider making permissive policy explicit in fleet-oriented constructors while
  keeping `Team.local(...)` clearly documented as demo/local convenience.

Concrete files:

- `coactra/src/coactra/workspace/integrations/mcp.py`
- `coactra/src/coactra/workspace/integrations/memory.py`
- `coactra/src/coactra/workflow/runtime/tools.py`
- `coactra/src/coactra/workflow/backends/durable_langgraph.py`
- `coactra/src/coactra/team/facade.py`

### 4. Memory Backend Is Too Broad For Existing Knowledge

The old memory contract required `remember`, `recall`, `capabilities`, `dump`, and
`ingest`.
That is too much for read-only existing knowledge, query-only RAG, SQL-backed search,
MCP resource search, or custom user systems. It also forces some implementations to
fake export behavior.

Recommendation:

- Split the contract:
  - Core: `recall(query, scope, k)`
  - Optional writer: `remember(events, scope)`
  - Optional migration/export: `capabilities`, `dump`, `ingest`
- Add a callable adapter for simple recall sources.
- Treat ingestion/export as migration tools, not the main memory path.

This directly supports the design goal: use existing knowledge without repeatedly
re-ingesting and rebuilding.

Concrete files:

- `coactra/src/coactra/memory/backends/base.py`
- `coactra/src/coactra/memory/facade.py`
- `coactra/src/coactra/agent/memory.py`

### 5. LangGraph Adapter Owns Too Much Coactra-Specific Semantics

`WorkflowEngine.start/resume` is a strong seam. The LangGraph durable backend is not
just an adapter; it owns document compilation, node types, CEL, Jinja, fanout,
interrupts, verification, sub-procedures, and done criteria.

Recommendation:

- Keep `WorkflowEngine` public and stable.
- Treat the current LangGraph backend as experimental adapter code.
- Move LangGraph document compiler helpers out of public exports.
- Let LangGraph own graph execution and retries. Let Coactra own ledger, approval
  evidence, policy hooks, and scope.

Concrete files:

- `coactra/src/coactra/workflow/runtime/durable.py`
- `coactra/src/coactra/workflow/backends/durable_langgraph.py`
- `coactra/src/coactra/workflow/runtime/defaults.py`

### 6. Approval And Durability Are Split Across Too Many Modules

The work ledger is one of Coactra's strongest modules: leases, attempts, retries,
pauses, decisions, budgets, usage, artifacts, and audit are behind one interface.
But approval state is also represented by runtime approval stores, and agent workflow
has checkpoint stores too.

Recommendation:

- Make the work ledger the fleet source of truth.
- Adapt runtime interrupts into ledger approval requests.
- Privatize or delete standalone `ApprovalStore` unless a concrete runtime needs it.
- Keep engine thread IDs as runtime state; keep business/audit state in the ledger.

Concrete files:

- `coactra/src/coactra/workflow/ledger/service.py`
- `coactra/src/coactra/workflow/ledger/domain/models.py`
- `coactra/src/coactra/workflow/runtime/approval.py`
- `coactra/src/coactra/workflow/ledger_facade.py`
- `coactra/src/coactra/agent/checkpoint.py`

### 7. Runtime And Workspace Inputs Need More Flexible Normalization

`memory=` already accepts backend names and backend objects. `workspace=` is more
rigid and treats values as local paths. `AgentRuntimePort` requires both `run` and
`stream`, but many bring-your-own runtimes only have `run`.

Recommendation:

- Accept `Workspace`, workspace backend, path-like, or config mapping at
  `workspace=`.
- Add a run-only runtime adapter. Streaming can be optional or synthesized as one
  final event.
- Prefer callable/object normalization over asking users to write full adapter
  classes for common cases.

Concrete files:

- `coactra/src/coactra/agent/runtime_wiring.py`
- `coactra/src/coactra/workspace/desk.py`
- `coactra/src/coactra/agent/ports.py`

### 8. A2A And Skill Metadata Should Have One Wire Conversion Owner

Coactra already has the right instinct: A2A outbound uses official SDK concepts and
does not try to own inbound serving. But Agent Card conversion appears in multiple
places.

Recommendation:

- Keep `Skill` as metadata/discovery/routing, not a new execution DSL.
- Align `Skill` fields with A2A Agent Card skill metadata and MCP Agent Skills where
  useful.
- Put all A2A wire conversion in one adapter module.
- Do not invent a custom A2A wire protocol.

Concrete files:

- `coactra/src/coactra/agent/skills.py`
- `coactra/src/coactra/agent/adapters/a2a.py`
- `coactra/src/coactra/workflow/ledger/adapters/a2a.py`

## What To Remove Or Demote

- Keep LangGraph document compiler helpers adapter-only.
- Keep `coactra.agent.recipes.code_change(...)` as a recipe/example, outside the
  core `Workflow` facade.
- Standalone runtime `ApprovalStore` if the ledger can own approval state.
- Mandatory memory export methods from the core backend protocol.
- Public sync/async identity protocol duplication if one async exchanger seam plus
  `as_async_exchanger(...)` is enough.
- Any "learning" or "reasoning replay" public surface that is not currently used by
  a shipped example or host integration. Keep the idea in docs until it has real call sites.

## What To Keep

- `Scope` as the common tenant/resource vocabulary.
- No-passthrough token exchange. This is a real differentiator.
- `Policy` as a first-class control point, but make it present at more seams.
- `WorkManager` and SQL ledger. This is deep and valuable.
- `WorkflowEngine.start/resume` as the runtime adapter seam.
- MCP and A2A as optional adapters.
- Memory as query-first, write-optional, backend-owned ranking/consolidation.

## Suggested Roadmap

### Phase 1: Public Surface Cleanup

- Decide the single public workflow vocabulary.
- Move code-change workflow into a recipe module.
- Hide LangGraph compiler helpers from `coactra.workflow.__all__`.
- Introduce or promote `AgentSpec` only if it replaces the wide `add_agent` shape.

### Phase 2: Security And Policy Locality

- Add read checks to MCP memory recall.
- Route journal distillation through workspace confinement.
- Add actor/scope/context to durable tool invocation.
- Unify `Policy` and directory `Authorizer` adapter shapes.

### Phase 3: Bring-Your-Own Component Flexibility

- Split memory protocols into recall/write/export.
- Add callable recall adapter.
- Add workspace normalization.
- Add run-only runtime adapter.

### Phase 4: Fleet Runtime Model

- Make work ledger the approval/checkpoint audit source.
- Keep runtime thread IDs as engine-specific state.
- Document Temporal/LangGraph/Prefect/DBOS/Dapr as injected engines, not Coactra's
  own execution model.

## Hard Questions Before Building More

1. Is Coactra a control plane or a framework? If both, which public object proves it?
2. When a user says "workflow", do they mean authored playbook, durable runtime,
   ledger work order, or induced procedure?
3. Can a user plug in a read-only internal search function as memory in under five
   lines?
4. Can every tool/resource access answer: who acted, under which scope, under which
   policy decision, with what evidence?
5. Which features are needed by current host integrations, and which are future product dreams?
6. If LangGraph, Temporal, or Pydantic AI already owns a behavior, what exactly does
   Coactra add besides a wrapper?

## Industry Notes

- MCP is an open protocol for connecting LLM applications to external data sources
  and tools, with hosts, clients, and servers communicating through JSON-RPC. Its
  own docs frame tools, resources, prompts, sampling, roots, and elicitation as
  protocol primitives, not as a mandate for app architecture.
- MCP architecture docs state that MCP does not dictate how AI applications use LLMs
  or manage context. That supports Coactra being a host/control shell rather than a
  replacement agent runtime.
- MCP Agent Skills are portable instruction sets with `SKILL.md` and optional
  references/assets. Coactra should interoperate with that shape rather than invent a
  richer skill runtime.
- A2A describes MCP and A2A as complementary: MCP is how an agent uses tools and
  resources; A2A is how agents partner or delegate.
- Pydantic AI, OpenAI Agents SDK, CrewAI, LangGraph, LlamaIndex, and AutoGen already
  cover large parts of agent loops, workflows, memory/data connectors, and
  orchestration. Coactra should integrate with them through small seams.
- RAG and ReAct research both support Coactra's direction: agents improve by using
  external knowledge and tools, but the library should preserve provenance, explicit
  state, and controlled actions instead of hiding everything in memory.

Sources:

- MCP introduction: https://modelcontextprotocol.io/docs/getting-started/intro
- MCP specification: https://modelcontextprotocol.io/specification/2025-06-18
- MCP architecture: https://modelcontextprotocol.io/docs/learn/architecture
- MCP Agent Skills: https://modelcontextprotocol.io/docs/develop/build-with-agent-skills
- A2A specification: https://a2a-protocol.org/latest/specification/
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- CrewAI docs: https://docs.crewai.com/
- LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview
- Pydantic AI docs: https://pydantic.dev/docs/ai/overview/
- LlamaIndex docs: https://developers.llamaindex.ai/python/framework/
- AutoGen docs: https://microsoft.github.io/autogen/stable/
- RAG paper: https://arxiv.org/abs/2005.11401
- ReAct paper: https://arxiv.org/abs/2210.03629
