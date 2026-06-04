# Multi-Agent Policy

Use this when one agent may ask another agent for help and you need policy before transport.

What it demonstrates:

- `PolicyGatedCollaborator`
- tenant-qualified `AgentRef`
- cross-tenant denial before the wire is touched
- the seam where `OfficialA2ATransport` would go in production

Run from the repo root:

```bash
PYTHONPATH=agent/src python3 examples/projects/multi_agent_policy/app.py
```

Production swap:

```python
from coactra.agent.adapters import OfficialA2ATransport
```
