# Coactra

Coactra is a Python library for building AI agent applications. The design is **three nouns**:

- **Agent** — one worker. Thinks, calls tools and MCP servers, holds memory, and publishes a discoverable card.
- **Team** — who exists and how they relate. A roster of Agents with a capability-matching policy and a who-may-talk rule.
- **Workflow** — a playbook and the manager that runs it. Plans steps, assigns each to an Agent from the Team, and drives every step to done — durably, with retries and approvals.

Everything a developer touches goes through a single door:

```python
from coactra import Agent

agent = await Agent.create(model="claude-sonnet-4-5")
answer = await agent.run("Summarize the incident and name the first check.")
print(answer)
```

That is the intended shape: name things, don't build them. No object graphs. No port injection.

!!! warning "Alpha — surface is settling"
    Coactra 0.0.x is alpha. `Agent` is the only public noun shipped so far. `Team` and
    `Workflow` are fully designed and coming next. Breaking changes will happen before 1.0
    without back-compat shims. Pin your version.

## Mental model

```
Team      = the roster        — who exists, who may talk, what each agent can do
Agent     = a worker          — thinks, uses tools + MCP, remembers
Workflow  = a playbook runner — assigns steps to Agents, drives to done
```

A goal arrives → **Workflow** picks or plans a playbook → assigns each step to an **Agent** from the **Team** → drives every step to done. An Agent step may delegate to a peer (A2A). That is the entire system.

The internal AI engine (`coactra.ai`) handles model routing through litellm and thinking-model adaption. Auth is cross-cutting: a token's scopes slice the agent's gateway tools; skills are published as an A2A Agent Card for discovery.

## Next steps

- [Quickstart](getting-started/quickstart.md) — install, hello agent, streaming, structured output, tools, gateway + auth, memory, workspace, skills.
- [Architecture](concepts/architecture.md) — the 3-noun model in detail and how they compose.
- [Library Map](concepts/library-map.md) — public names with available vs designed tags.
- [API Index](API_INDEX.md) — the full public surface.
