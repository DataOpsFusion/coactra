# Support Ticket Agent

A composed agent without subclassing. The example wires small local ports for AI,
memory, workspace, and durable work, then handles one support ticket.

```bash
python3 examples/support_ticket_agent.py
```

Shows:

- dependency injection through `make_agent(...)`
- plain functions for app behavior
- a tiny in-memory `AIPort`, `MemoryPort`, `WorkspacePort`, and `WorkPort`

Use this when you want to understand the port shape before writing real adapters.

Source: [examples/support_ticket_agent.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/support_ticket_agent.py)
