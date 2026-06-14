# Security Policy

## Supported Versions

Coactra is in **alpha** (`0.0.x`). Security fixes land on the latest `main` / `dev`
branch and the most recent tagged release. Older alpha tags may not receive backports.

| Version | Supported |
|---------|-----------|
| `0.0.x` (latest tag) | Yes |
| Pre-release commits | Best-effort on `main` |

## Reporting a Vulnerability

**Do not** open public GitHub issues for undisclosed security problems.

1. Use [GitHub private vulnerability reporting](https://github.com/DataOpsFusion/coactra/security/advisories/new) on the repository, **or**
2. Email the maintainers through the contact listed on the PyPI project page.

Include: affected version, reproduction steps, impact, and any suggested fix.

We aim to acknowledge reports within **5 business days** and provide a remediation
timeline when a fix is confirmed.

## Security Posture (Library)

Coactra is a composition library. **Hosts** remain responsible for authentication,
authorization, network policy, secret storage, and sandboxing.

Built-in guardrails:

- **Token passthrough is rejected** — use RFC 8693 exchange (`KeycloakExchanger` /
  `AsyncKeycloakExchanger`), not raw bearer passthrough.
- **Workspace local exec is opt-in** — disabled by default; not a process sandbox.
- **Inbound A2A serving is host-owned** — wire the official `a2a-sdk` server and
  authorize before calling `agent.run()`.

See [docs/concepts/security.md](docs/concepts/security.md) for the full threat model.
