# Offline Agent SDK

This example shows the higher-level agent SDK shape using an offline
`pydantic-ai` `FunctionModel`.

## Demonstrates

- `coactra.agent.sdk.Agent`
- streaming run events
- offline model behavior with no API key
- the seam for swapping in a real model id

## Naming Style

The model callback is intentionally private because it is local wiring, while
`main()` is the runnable entrypoint:

```python
def _model(messages, info):
    ...


async def main() -> None:
    ...
```

## Run

```bash
python3 examples/elegant_agent.py
```

Source: [https://github.com/DataOpsFusion/coactra/blob/main/examples/elegant_agent.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/elegant_agent.py)
