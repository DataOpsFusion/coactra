# Coactra Agent Runtime Design

**Status:** current Team-first alpha contract.

## Goal

`Agent` is a runtime actor, not the public assembly door. It remains a thin
composition shell over pydantic-ai with Team-owned wiring for models, tools,
memory, workspace, peer delegation, and tracing.

## Public shape

Application code should prefer:

```python
from coactra import Policy, Scope, Team

team = Team(scope=Scope.local(), policy=Policy.permissive())
agent = await team.add_agent(
    name="sre-1",
    model_capability="fast-chat",
    gateway="https://gateway/mcp",
    auth=token_source,
    memory="graphiti",
    workspace="./desk",
    peers=["security-agent"],
    skills=[...],
    instructions="Be terse.",
)
```

`Agent.run(...)` and `agent.send(...).stream()` remain the runtime interaction
surface after construction.

## Decisions

1. **Construction is Team-owned.**
   - `Team.add_agent(...)` is the public way to build runtime agents.
   - Standalone Team-less agent construction is removed.

2. **Capabilities are named, not manually composed.**
   - `model_capability=` is the preferred model path.
   - `memory=`, `workspace=`, `gateway=`, `peers=`, `skills=` stay named seams.
   - `model=` remains a temporary escape hatch for raw pydantic-ai models.

3. **Model access is governed.**
   - Agents request capabilities.
   - `Policy` and `ModelResolver` choose allowed routes.
   - Providers remain behind adapters.

4. **Memory is an automatic connector.**
   - Auto-recall before the turn.
   - Auto-remember after the turn.
   - Backend owns ranking and storage.
   - Coactra owns scope, provenance, policy, and injection limits.

5. **Workspace is a guarded capability.**
   - File tools are added when configured.
   - command execution remains allowlist-gated.

6. **A2A remains separate from normal tool declaration.**
   - `peers=` defines outbound delegation targets.
   - remote and local peers are translated into delegation tools.
   - capability discovery is curated through Agent Cards.

7. **Agent Cards advertise effective capability, not raw tool power.**
   - skills are curated
   - credentials are never exposed
   - discovery does not imply authority

## Internal boundaries

- Coactra owns orchestration around pydantic-ai.
- Pydantic AI owns runtime model execution.
- LiteLLM is an adapter path for provider normalization.
- MCP and A2A stay external protocols wrapped by Coactra policy, scope, and run semantics.

## Current runtime contract

- `agent.run(message, output=...)`
- `agent.send(message).stream()`
- `agent.card`
- peer delegation tools
- memory and workspace capabilities
- Team-governed routing and policy checks
