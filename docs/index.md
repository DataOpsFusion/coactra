# Coactra Docs

Coactra is a composition and persistence library for multi-agent workflows:
`Team`, `Workflow`, and `WorkManager` are the core; `Agent` is a thin shell over
pydantic-ai with memory, workspace, MCP, and peer delegation wiring.

Start with the [Quickstart](getting-started/quickstart.md), then use the example
and production guides when you are ready to wire real backends.

## Install

```bash
pip install "coactra[agent]"
```

Use extras to add the backends you need:

```bash
pip install "coactra[sql]"
pip install "coactra[graphiti]"
pip install "coactra[langgraph]"
```

## Main Guides

- [Quickstart](getting-started/quickstart.md): build a small function-first incident triage app.
- [Bring Your Own Stack](getting-started/bring-your-own.md): pydantic-ai models, OAuth, and A2A serving without Coactra glue.
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
