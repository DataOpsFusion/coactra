"""ProcedureStore — the tenant-scoped library that makes "reuse the flow" real.

Deliberately tiny: save / get / list, keyed by Scope. This is the easy piece to balloon,
so it stays minimal. The ONE working default is in-memory and tenant-isolated; swap in a
durable backend (CouchDB / Postgres) behind the same Protocol later.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from coactra.scope import Scope
from coactra.workflow.domain.models import Procedure


@runtime_checkable
class ProcedureStore(Protocol):
    def save(self, procedure: Procedure, scope: Scope) -> None:
        """Persist (or overwrite) a procedure by name within scope."""
        ...

    def get(self, name: str, scope: Scope) -> Procedure | None:
        """Fetch a procedure by name within scope, or None."""
        ...

    def list(self, scope: Scope) -> list[Procedure]:
        """List all procedures in scope."""
        ...

    def exists(self, name: str, scope: Scope) -> bool:
        """Return True when a procedure exists within scope."""
        ...

    def replace(self, procedure: Procedure, scope: Scope) -> None:
        """Replace an existing procedure, raising KeyError when missing."""
        ...

    def delete(self, name: str, scope: Scope) -> bool:
        """Delete a procedure by name, returning whether it existed."""
        ...


class InMemoryProcedureStore:
    """In-memory, tenant-isolated procedure library (the default ProcedureStore)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Procedure]] = {}

    def _bucket(self, scope: Scope) -> dict[str, Procedure]:
        return self._store.setdefault(scope.key, {})

    def save(self, procedure: Procedure, scope: Scope) -> None:
        self._bucket(scope)[procedure.name] = procedure

    def get(self, name: str, scope: Scope) -> Procedure | None:
        return self._bucket(scope).get(name)

    def list(self, scope: Scope) -> list[Procedure]:
        return list(self._bucket(scope).values())

    def exists(self, name: str, scope: Scope) -> bool:
        return name in self._bucket(scope)

    def replace(self, procedure: Procedure, scope: Scope) -> None:
        bucket = self._bucket(scope)
        if procedure.name not in bucket:
            raise KeyError(procedure.name)
        bucket[procedure.name] = procedure

    def delete(self, name: str, scope: Scope) -> bool:
        bucket = self._bucket(scope)
        if name not in bucket:
            return False
        del bucket[name]
        return True
