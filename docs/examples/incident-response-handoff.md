# Incident Response Handoff

The smallest normal Coactra app: open durable work, ask an agent for a handoff,
checkpoint the draft, complete the work order, and inspect audit events.

```bash
python3 examples/incident_response_handoff.py
```

Shows:

- `make_agent(...)` as the local agent facade
- `WorkManager` and `WorkOrder` as the durable work boundary
- artifacts and event history

Local defaults:

- `WorkManager()` uses an in-memory store
- `make_agent(...)` uses a fake AI port unless you inject a real one

Source: [examples/incident_response_handoff.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/incident_response_handoff.py)
