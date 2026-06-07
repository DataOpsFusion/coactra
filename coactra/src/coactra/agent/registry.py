"""Fleet registry primitives for resolving named remote agents.

This is intentionally small: it models discovery data and converts entries into
RemotePeer configs. Durable or network-backed registries can implement the same
protocol later without changing Agent.create.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence, Mapping, runtime_checkable

from coactra.agent.peers import RemotePeer


@dataclass(frozen=True)
class FleetEntry:
    """Registered remote agent endpoint and optional discovery metadata."""

    name: str
    endpoint: str
    tenant: str = "default"
    audience: str | None = None
    card: Mapping[str, Any] | None = None
    token_provider: Any | None = None
    client: Any | None = None
    timeout: float = 60.0
    delegation_chain: Sequence[Mapping[str, Any]] | None = None
    message_builder: Any | None = None

    def remote_peer(self) -> RemotePeer:
        return RemotePeer(
            name=self.name,
            endpoint=self.endpoint,
            audience=self.audience,
            tenant=self.tenant,
            token_provider=self.token_provider,
            client=self.client,
            timeout=self.timeout,
            delegation_chain=self.delegation_chain,
            message_builder=self.message_builder,
        )


@runtime_checkable
class FleetRegistry(Protocol):
    """Lookup interface used by Agent.create for named remote peers."""

    def resolve(self, name: str, *, tenant: str | None = None) -> FleetEntry | None: ...


class InMemoryFleetRegistry:
    """Simple process-local fleet registry for tests and single-process hosts."""

    def __init__(self, entries: Sequence[FleetEntry] | None = None) -> None:
        self._entries: dict[tuple[str, str], FleetEntry] = {}
        for entry in entries or ():
            self.add(entry)

    def add(self, entry: FleetEntry) -> FleetEntry:
        self._entries[(entry.tenant, entry.name)] = entry
        return entry

    def register(
        self,
        *,
        name: str,
        endpoint: str,
        tenant: str = "default",
        audience: str | None = None,
        card: Mapping[str, Any] | None = None,
        token_provider: Any | None = None,
        client: Any | None = None,
        timeout: float = 60.0,
        delegation_chain: Sequence[Mapping[str, Any]] | None = None,
        message_builder: Any | None = None,
    ) -> FleetEntry:
        return self.add(FleetEntry(
            name=name,
            endpoint=endpoint,
            tenant=tenant,
            audience=audience,
            card=card,
            token_provider=token_provider,
            client=client,
            timeout=timeout,
            delegation_chain=delegation_chain,
            message_builder=message_builder,
        ))

    def resolve(self, name: str, *, tenant: str | None = None) -> FleetEntry | None:
        if tenant is not None:
            entry = self._entries.get((tenant, name))
            if entry is not None:
                return entry
        for (entry_tenant, entry_name), entry in self._entries.items():
            if entry_name == name and (tenant is None or entry_tenant == tenant):
                return entry
        return None


__all__ = ["FleetEntry", "FleetRegistry", "InMemoryFleetRegistry"]
