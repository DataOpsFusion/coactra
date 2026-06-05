# Examples

The examples are meant to be copied. They are small, local, and dependency-light so you can run them before wiring real providers.

## How To Run From The Repo

Because this repository is a multi-package workspace, run examples with the package `src` directory on `PYTHONPATH` unless you have installed the packages already.

```bash
PYTHONPATH=agent/src:jobs/src python3 examples/basic_incident_triage.py
```

If you installed the packages with `pip install -e`, you can run the same files without `PYTHONPATH`.

## Recommended Starting Points

| If you are building... | Start here | Why |
|---|---|---|
| a normal single-agent app | [../examples/basic_incident_triage.py](../examples/basic_incident_triage.py) | Smallest complete app using `make_agent` and `WorkManager`. |
| support or helpdesk memory | [../examples/projects/customer_support_memory](../examples/projects/customer_support_memory) | Shows scoped `remember` and `recall`. |
| durable jobs or releases | [../examples/projects/release_runner](../examples/projects/release_runner) | Shows submit, claim, start, checkpoint, complete, artifacts, events. |
| a file-backed agent desk | [../examples/projects/workspace_research_desk](../examples/projects/workspace_research_desk) | Shows workspace files, handoff notes, and capability manifests. |
| multi-agent collaboration | [../examples/projects/multi_agent_policy](../examples/projects/multi_agent_policy) | Shows policy-gated A2A placement and cross-tenant denial. |
| custom port injection | [../examples/function_first_agent.py](../examples/function_first_agent.py) | Advanced proof that structural ports can be plain function objects. |

## Sample Projects

### Customer Support Memory

Run:

```bash
PYTHONPATH=memory/src python3 examples/projects/customer_support_memory/app.py
```

Use this shape when your app needs to remember prior tickets, customer preferences, operational lessons, or conversation facts.

### Release Runner

Run:

```bash
PYTHONPATH=jobs/src python3 examples/projects/release_runner/app.py
```

Use this shape when work should have a stable id, lifecycle status, retries, checkpoints, artifacts, and audit events.

### Workspace Research Desk

Run:

```bash
PYTHONPATH=workspace/src python3 examples/projects/workspace_research_desk/app.py
```

Use this shape when an agent needs files, notes, a handoff, and a passive list of capabilities to remount next session.

### Multi-Agent Policy

Run:

```bash
PYTHONPATH=agent/src python3 examples/projects/multi_agent_policy/app.py
```

Use this shape when one agent can ask another agent for help. The example uses a fake local transport so you can see that policy denies cross-tenant calls before any wire call happens.

## Design Rule

Application behavior should stay function-first:

```python
def triage_incident(agent, work, incident: str):
    ...
```

Use classes when they own durable state or an external boundary:

- `WorkManager`, `SqlWorkStore`
- `Memory`, memory backends
- `Workspace`, workspace backends
- A2A transports
- OAuth/Keycloak exchangers

That is the intended library style. Coactra gives you stable seams; it should not force a subclass tree into every app.
