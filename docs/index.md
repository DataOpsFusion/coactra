# Coactra Docs

Coactra is a block-kit orchestration library for AI workloads. Start small with
`Agent.create(...)`, grow into `Team.local(...)`, then add explicit `Policy`,
`Scope`, memory, workspace, MCP, peer delegation, and workflow backends when the
host needs them.

Start with the [Quickstart](getting-started/quickstart.md), then use the example
and production guides when you are ready to wire real backends.

## Install

```bash
pip install "coactra[agent]"
```

Use extras to add only the backends you need:

```bash
pip install "coactra[sql]"       # SQL work ledger / stores
pip install "coactra[graphiti]"  # Graphiti-backed memory
pip install "coactra[oauth]"     # Keycloak/OAuth token exchange
```

`coactra[langgraph]` remains available for the optional LangGraph adapter, but
it is no longer required for the default durable workflow engine.

## Main Guides

- [Quickstart](getting-started/quickstart.md): build a small function-first incident triage app.
- [Bring Your Own Stack](getting-started/bring-your-own.md): existing models, tools, memory, workspace, and MCP gateway.
- [Examples](examples/index.md): runnable scripts and sample projects.
- [API Index](API_INDEX.md): the public API surface.
- [Production](operations/production.md): SQL work store, scope consistency, auth, and deployment posture.
- [Architecture](concepts/architecture.md): package boundaries and adoption rules.

## Documentation Flow

Documentation follows the same branch flow as code:

```text
feature/* -> dev -> main -> GitHub Pages
```

Pull requests into `dev` and `main` build the docs as a check. Only `main`
deploys the public GitHub Pages site.
