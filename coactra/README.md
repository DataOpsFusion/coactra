# coactra

Convenience installer and dependency-light shell for the modular Coactra libraries. It contains shared scope, error, plugin, and Kernel/Session DTOs, but no backend business logic.

Install only the capability you need:

```bash
pip install coactra[memory]
pip install coactra[workspace]
pip install coactra[orchestration]
pip install coactra[agent]
pip install coactra[all]
```

Each capability remains independently installable, such as `pip install coactra-memory`.


## Dependency-Light Shell

```python
from coactra.kernel import Kernel, Task
from coactra.scope import CoactraScope


def handler(context, task):
    return {"tenant": context.scope.tenant_id, "input": dict(task.input)}


session = (
    Kernel.builder()
    .with_handler("echo", handler)
    .build()
    .session(CoactraScope(tenant_id="acme", namespace="support"))
)
result = await session.run(Task("echo", {"x": 1}))
```
