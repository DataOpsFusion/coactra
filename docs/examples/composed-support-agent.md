# Composed Support Agent

Use this when you want richer app composition without building an inheritance
framework. The example wires small structural ports with plain functions and
`SimpleNamespace` objects.

## Demonstrates

- function-backed AI, memory, workspace, workflow, organization, and work ports
- `make_agent(...)` as the composition boundary
- async memory recall
- `WorkManager` adapted without subclassing

## Function Style

Use `make_*` for local port factories, `build_*` for composition roots, and verb
phrases for application behavior:

```python
def make_ai_port():
    ...


def make_memory_port():
    ...


def build_support_agent(...):
    ...


async def triage_incident(agent, incident_text: str):
    ...
```

## Run

```bash
python3 examples/function_first_agent.py
```

Source: [https://github.com/DataOpsFusion/coactra/blob/main/examples/function_first_agent.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/function_first_agent.py)
