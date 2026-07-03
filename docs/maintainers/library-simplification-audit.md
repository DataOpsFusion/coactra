# Library Simplification Audit

Date: 2026-07-02

Scope: Coactra as a general library for AI workloads.

## Positioning

Coactra should be a policy-aware composition library for AI workloads, not an
agent framework, memory framework, or workflow engine. The public story should be:

> Bring your own agent runtime, workflow engine, memory/RAG stack, and tools.
> Coactra supplies tenant scope, policy gates, model routing, delegated identity,
> and small composition primitives.

That positioning keeps adoption broad because users can keep Pydantic AI,
LangGraph, LlamaIndex, AutoGen, CrewAI, OpenAI Agents SDK, or direct provider
calls where those tools already fit.

## What To Stop Owning

- Model/tool execution loops. Pydantic AI already positions itself as a Python
  agent framework for production GenAI apps with model-provider support,
  observability, evals, MCP/UI, human-in-the-loop, durable execution, and graph
  support. Source: <https://pydantic.dev/docs/ai/overview/>.
- Durable workflow graph runtime. LangGraph is already focused on long-running,
  stateful agents with durable execution, persistence, memory, streaming, and
  human-in-the-loop controls. Source:
  <https://docs.langchain.com/oss/python/langgraph/overview>.
- RAG ingestion, indexing, and query engines. LlamaIndex already owns
  context-augmented LLM apps, data connectors, indexes, query/chat engines,
  agents, workflows, and eval integrations. Source:
  <https://developers.llamaindex.ai/python/framework/>.
- Multi-agent event runtimes and conversational agent frameworks. AutoGen
  already exposes an event-driven multi-agent core plus higher-level AgentChat
  APIs, MCP integration, Docker code execution, and distributed runtime support.
  Source: <https://microsoft.github.io/autogen/stable/>.
- Hosted-style agent loop primitives. OpenAI Agents SDK already defines agents,
  handoffs, guardrails, sessions, tracing, MCP, human-in-the-loop, and sandboxed
  agent support. Source: <https://openai.github.io/openai-agents-python/>.
- Business process orchestration. CrewAI already covers crews, flows, tasks,
  guardrails, memory, knowledge, observability, and human-in-the-loop triggers.
  Source: <https://docs.crewai.com/>.

## What Coactra Should Own

- `Scope`: canonical tenant and namespace ownership boundaries.
- `Policy`: explicit allow/deny gates at routing and execution points.
- `ModelResolver` / `ModelRoute`: governed model selection without owning the
  provider loop.
- Delegated identity: token exchange, chain tracking, and no token passthrough.
- Team composition: the smallest object that wires scope, policy, models, memory,
  workspace, peers, and workflow adapters together.
- Optional adapters to established protocols and frameworks: MCP, A2A, Pydantic
  AI models, LangGraph, LlamaIndex, OpenAI Agents SDK, AutoGen, and CrewAI.

## Memory And Knowledge

Coactra should prefer existing knowledge stores over re-ingestion. The memory
contract should be query-first:

- `recall(...)` reads from an existing backend through an adapter.
- `remember(...)` writes only when the caller explicitly wants Coactra to add new
  memories.
- ingestion/import/export are explicit migration tools, not the default path for
  connecting data.

This lets users attach Mem0, Graphiti, LlamaIndex, vector databases, SQL search,
files, or company knowledge APIs without rebuilding the same memory corpus for
each new agent framework.

## Current Simplification Decisions

- Removed pure compatibility shim modules in `ai`, `workflow`, and `workspace`.
  Alpha status makes this acceptable and it reduces import ambiguity.
- Removed the public embedding wrapper. Provider libraries and memory engines
  should own embeddings; Coactra keeps only private replay ranking.
- Removed the fake async/Postgres org-store wrapper. It did not provide true
  async I/O and created a misleading public surface.
- Collapsed duplicate package-local `Scope` subclasses into direct aliases over
  the shared tenant/namespace base.
- Gated MCP toolset tests behind the optional MCP dependency instead of requiring
  gateway integration packages in the default suite.
- Replaced deprecated `MCPServerStdio` construction with direct `MCPToolset`
  pass-through. Real tests now cover streamable HTTP; subprocess stdio works
  when the execution environment allows child stdio handshakes, so prefer
  streamable HTTP for fleet/runtime deployments and keep stdio as a local server
  path.

## Remaining Candidates

- Reconsider `make_default_workflow_engine()`. It is a wrapper over
  `make_workflow_engine("langgraph", ...)`; keep it only if the name is part of
  the public teaching surface.
- Reconsider `ToolInvoker`. If it is only a single async callable shape, a
  `Callable[..., Awaitable[Any]]` may be enough. Keep the protocol only if the
  name helps external adapters.
- Keep `AgentRuntimePort`. It is a useful boundary for "bring your own runtime"
  and supports Coactra's library positioning.
- Do not deepen the workflow DSL. Prefer adapters to LangGraph, CrewAI,
  Temporal, Prefect, or direct user code.
- Keep MCP and A2A as optional protocol adapters, not hard base dependencies.

## Grill Question

Should Coactra publicly define itself as a policy-aware composition library over
existing agent/RAG/workflow runtimes, rather than an agent framework?

Recommended answer: yes. That answer implies the next cleanup pass should remove
or de-emphasize runtime-shaped abstractions and strengthen scope, policy, model
routing, identity, and adapter contracts.
