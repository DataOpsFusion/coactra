# Coactra

Coactra is a modular toolkit for orchestrating agents that do real work. `coactra-work` adds durable work orders and optional bridges to established execution runtimes. Each capability
is independently installable, while `coactra-agent` optionally composes them into one
runtime through narrow ports.

See [LIBRARIES.md](LIBRARIES.md) for package boundaries and installation options.

```bash
make test       # full suite after installing every package's dev dependencies
make test-core  # dependency-light local suite
```
