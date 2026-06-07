# Resolution Memory

A local memory project for repeat support issues.

```bash
python3 examples/projects/resolution_memory/app.py
```

Uses `Memory` with `make_backend("inprocess")`. For production, replace the backend
with mem0 or Graphiti and keep the `record_resolution` / `suggest_fix` functions.
