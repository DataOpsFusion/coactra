# Multi-Agent Policy

Use this when one agent may ask another agent for help and you need policy before
transport.

## Demonstrates

- `PolicyGatedCollaborator`
- tenant-qualified `AgentRef`
- cross-tenant denial before the wire is touched
- the seam where `OfficialA2ATransport` belongs in production

## Run

```bash
python3 examples/projects/multi_agent_policy/app.py
```

## Production Swap

```python
from coactra.agent.adapters import OfficialA2ATransport
```

Source: [https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/multi_agent_policy](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/multi_agent_policy)
