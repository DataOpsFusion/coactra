# Bring Your Own Stack

Use Coactra as composable blocks around your existing model, tools, memory, workspace, and MCP gateway.

## Existing model

```python
team = Team.local(model=my_model, tenant_id="acme", namespace="existing-stack")
agent = await team.add_agent("existing-model-agent")
```

## Multiple models

```python
team = Team.local(model=cheap_model, tenant_id="acme")
smart = await team.add_agent("smart-agent", model=smart_model)
```

## Named routes

```python
team.add_model("tool-agent", my_model, api_base=api_base, api_key=api_key)
agent = await team.add_agent("tool-agent", model_capability="tool-agent", gateway=gateway)
```

`model_capability=` selects a named route. Normal users should prefer `Team.local(...)`,
per-agent `model=...`, or `team.add_model(...)` instead of constructing routing
internals.
