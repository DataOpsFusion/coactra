# Customer Support Memory

Use this when your app needs to remember what happened in earlier conversations or tickets.

What it demonstrates:

- `coactra.memory.Memory`
- `make_backend("inprocess")` for local development
- tenant-scoped `remember` and `recall`
- application logic as plain functions

Run from the repo root:

```bash
PYTHONPATH=memory/src python3 examples/projects/customer_support_memory/app.py
```

Production swap:

```python
memory = Memory(backend=make_backend("graphiti", ...))
```
