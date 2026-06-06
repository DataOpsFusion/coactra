# Offline SRE Agent

The optional SDK shape using `pydantic-ai` with a local `FunctionModel`. It does
not call an external model.

```bash
python3 examples/offline_sre_agent.py
```

Requires:

```bash
pip install "coactra[agent]"
```

Use this only when you want the SDK loop. The stable first-run path is still
`make_agent(...)`.

Source: [examples/offline_sre_agent.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/offline_sre_agent.py)
