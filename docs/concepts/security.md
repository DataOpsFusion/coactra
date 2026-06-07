# Security Notes

Coactra is a library suite. The host application remains responsible for production authentication, authorization, network policy, secret management, and sandboxing. These notes define what the reusable code should and should not do.

## Token Handling

- Do not pass human or upstream bearer tokens through agents or tool servers.
- Use RFC 8693 token exchange semantics for delegated identity.
- `InProcessExchanger` is for local/test behavior and proves no-passthrough shape.
- `KeycloakExchanger` is the production-oriented adapter for Keycloak-compatible token endpoints.
- Treat `CachedAsyncTokenExchanger` as an in-process convenience cache, not an authorization source of truth.

## A2A Services

- Outbound A2A calls should go through collaboration policy before reaching the transport.
- Cross-tenant calls should be denied by default.
- Inbound A2A services should require a verifier in production.
- A2A request handlers should authorize requested capability, subject, audience, and tenant before invoking host runtime behavior.

## Workspace Safety

- Local file confinement is not a process sandbox.
- Local command execution is disabled by default for a reason.
- Use sandbox or remote workspace providers for untrusted tenants or untrusted commands.
- Workspace files, handoff notes, journals, and capability manifests must not contain long-lived secrets.
- Capability manifests should store references, not credentials.

## Memory Safety

- Memory events can become long-lived facts. Do not store raw secrets, credentials, payment data, or private contact details unless the host has a clear retention and deletion policy.
- Use `AuthorizedMemory` or host policy checks before shared namespace reads/writes.
- Export is lossy and should not be treated as a compliance-grade archival mechanism.

## Organization and Authorization

- The directory package models who exists, who reports to whom, and who may do what.
- External authorization enforcement should use an `Authorizer` such as OpenFGA or a host-supplied policy engine.
- Permission decisions should be auditable by the host application.

## Durable Work and Workflow

- Work orders may contain sensitive task details, approvals, artifacts, and audit metadata.
- Use SQL-backed work storage for production and protect the database accordingly.
- Human approval state must be durable if approvals can survive process restarts.
- Dangerous tool execution should be capability-gated before side effects.

## Minimum Production Checklist

- real token exchange configured
- inbound A2A verifier required
- workspace command execution sandboxed or disabled
- SQL work ledger configured
- durable workflow runtime persistence configured
- memory backend retention and deletion policy defined
- tenant isolation tests in place
