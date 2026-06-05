# Coactra Docs

Coactra is a Python library for agent applications that need durable work,
memory, workspace state, organization policy, and agent-to-agent collaboration.

Start with the [Quickstart](QUICKSTART.md), then use the interface and production
guides when you are ready to wire real backends.

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

- [Quickstart](QUICKSTART.md): build a small function-first incident triage app.
- [Examples](EXAMPLES.md): runnable sample projects for memory, durable work, workspace, and multi-agent policy.
- [Interface Map](INTERFACES.md): package roots and stable API surfaces.
- [Production](PRODUCTION.md): SQL work store, scope consistency, auth, and deployment posture.
- [Architecture](ARCHITECTURE.md): package boundaries and adoption rules.

## Release Flow

Documentation follows the same branch flow as code:

```text
feature/* -> dev -> main -> GitHub Pages
```

Pull requests into `dev` and `main` build the docs as a check. Only `main`
deploys the public GitHub Pages site.
