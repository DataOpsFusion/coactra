# Basic Incident Triage

Use this as the first example for a normal Coactra application. It combines a
plain incident workflow, `make_agent(...)`, and `WorkManager` without introducing
a class hierarchy.

## Demonstrates

- `make_agent(...)` with dependency-light defaults
- `WorkManager` and `WorkOrder`
- idempotency keys for repeated incidents
- plain functions for application behavior

## Function Style

The example keeps names action-oriented and specific:

```python
def incident_key(incident: str) -> str:
    ...


def submit_incident(work, scope, incident: str):
    ...


def draft_first_checks(agent, incident: str) -> str:
    ...


def triage_incident(incident: str) -> dict[str, str]:
    ...
```

## Run

```bash
python3 examples/basic_incident_triage.py
```

The default agent uses an in-process fake model, so the draft text is an echo-like
placeholder. Wire a real model for production behavior.

Source: [https://github.com/DataOpsFusion/coactra/blob/main/examples/basic_incident_triage.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/basic_incident_triage.py)
