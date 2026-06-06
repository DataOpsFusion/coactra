# coactra

Single-distribution package for Coactra: tenant-scoped work orders, memory, workspace, directory, AI, and agent composition with optional backend extras.

Install only the capability you need:

```bash
pip install coactra[memory]
pip install coactra[workspace]
pip install coactra[orchestration]
pip install coactra[agent]
pip install coactra[all]
```

The former split-package roots are compatibility paths; new installs should use
the single `coactra` distribution plus extras.


## Dependency-Light Work Order

```python
from coactra.jobs import WorkManager, WorkOrder, WorkScope

work = WorkManager()
scope = WorkScope(tenant_id="acme", namespace="support")
order = work.submit(WorkOrder(scope=scope, title="Triage checkout latency"))
print(order.id, order.status.value)
```

`coactra.kernel` and `coactra.plugins` are experimental shells. Start with the stable facades documented in `docs/API_INDEX.md`.
