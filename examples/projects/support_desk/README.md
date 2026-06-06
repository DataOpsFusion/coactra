# Support Desk

Combined helpdesk sample: agent draft, durable work orders, and ticket memory.

What it demonstrates:

- `make_agent` with in-process fake model
- `WorkManager` lifecycle (submit → claim → start → checkpoint → complete)
- `Memory.remember` / `Memory.recall` for prior resolutions
- plain functions for application behavior

Run from the repo root:

```bash
python3 examples/projects/support_desk/app.py
```

Production swaps:

```python
memory = Memory(backend=make_backend("graphiti", ...))
work = WorkManager(store=SqlWorkStore.from_url("postgresql+psycopg://..."))
```
