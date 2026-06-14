# Customer Support Memory

Modern Coactra examples use lazy builders instead of legacy route/profile construction.

```python
from coactra import Skill, Team

team = Team.local(model="openai:gpt-4.1-mini", tenant_id="acme")
agent = await team.add_agent(
    "agent",
    skills=[Skill("example")],
    instructions="Be concise and actionable.",
)
```

For multiple models:

```python
fast = await team.add_agent("fast")
smart = await team.add_agent("smart", model="anthropic:claude-sonnet-4")
```

For a reusable named route:

```python
team.add_model("senior", "anthropic:claude-sonnet-4")
senior = await team.add_agent("senior", model_capability="senior")
```
