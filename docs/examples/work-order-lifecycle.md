# Work Order Lifecycle

Use this when you need durable work state: leases, checkpoints, approvals, and
artifacts — not a one-shot function call.

## Demonstrates

- `WorkManager` as the lifecycle ledger
- `Scope` for tenant-scoped work
- checkpoint → approval → resume → complete
- audit event history

## Run

```bash
python3 examples/work/submit_and_complete.py
python3 examples/work/lifecycle_with_approval.py
```

## Function Style

Keep application behavior in named functions:

```python
def submit_publish_work(work: WorkManager, title: str) -> WorkOrder:
    ...

def run_publish_with_approval(work: WorkManager, title: str) -> dict[str, object]:
    ...
```

## Production Swap

```python
from coactra.jobs import SqlWorkStore, WorkManager

work = WorkManager(store=SqlWorkStore.from_url("postgresql+psycopg://..."))
```

See also [Work Orders](../operations/work-orders.md) and [Release Runner](release-runner.md).
