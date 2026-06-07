# Ticket Triage

A copyable support workflow: recall prior fixes, draft a triage note, open durable
work, checkpoint the result, and complete with an artifact.

```bash
python3 examples/projects/ticket_triage/app.py
```

Local defaults: fake AI, in-process memory, and in-memory work store. Production
replacements: real AI port, mem0/Graphiti memory, and `SqlWorkStore`.
