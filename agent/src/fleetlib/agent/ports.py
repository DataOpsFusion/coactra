"""The five sibling PORTS — the un-tangling seam.

agent wires ai/memory/workspace/workflow/organization, but consuming a sibling's CODE
would re-tangle the libraries (and lib-ai/organization have no code yet). So each sibling
is consumed through a NARROW local port Protocol with an in-process fake default — exactly
as the sibling `workflow` plan refused to import `fleetlib.ai` and used a local shape. The
real wiring (swap a fake for an adapter around the published sibling) happens downstream;
this library never imports `fleetlib.<sibling>`.

Each port is deliberately tiny: only the surface the Agent facade actually calls.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fleetlib.agent.scope import Scope


@runtime_checkable
class AIPort(Protocol):
    def complete(self, prompt: str) -> str:
        """Run one model completion (fleetlib.ai's job)."""
        ...


@runtime_checkable
class MemoryPort(Protocol):
    def learn(self, text: str, scope: Scope) -> None:
        """Persist a learned fact within scope (fleetlib.memory's job)."""
        ...

    def recall(self, query: str, scope: Scope) -> list[str]:
        """Recall facts matching query within scope."""
        ...


@runtime_checkable
class WorkspacePort(Protocol):
    def write(self, path: str, content: str, scope: Scope) -> None:
        """Write a file to the agent's persistent desk (fleetlib.workspace's job)."""
        ...

    def read(self, path: str, scope: Scope) -> str:
        """Read a file from the desk."""
        ...


@runtime_checkable
class WorkflowPort(Protocol):
    def run(self, name: str, scope: Scope) -> dict:
        """Run a named procedure within scope (fleetlib.workflow's job)."""
        ...


@runtime_checkable
class OrganizationPort(Protocol):
    def escalation_chain(self, agent_id: str, scope: Scope) -> list[str]:
        """Return the escalation chain for agent_id (fleetlib.organization's job)."""
        ...


# --- in-process fakes (the ONE working default per port) ------------------------------


class FakeAI:
    def complete(self, prompt: str) -> str:
        return f"completion:{prompt}"


class FakeMemory:
    def __init__(self) -> None:
        self._store: dict[str, list[str]] = {}

    def learn(self, text: str, scope: Scope) -> None:
        self._store.setdefault(scope.key, []).append(text)

    def recall(self, query: str, scope: Scope) -> list[str]:
        return [t for t in self._store.get(scope.key, []) if query in t]


class FakeWorkspace:
    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def write(self, path: str, content: str, scope: Scope) -> None:
        self._files[f"{scope.key}/{path}"] = content

    def read(self, path: str, scope: Scope) -> str:
        return self._files.get(f"{scope.key}/{path}", "")


class FakeWorkflow:
    def run(self, name: str, scope: Scope) -> dict:
        return {"procedure": name, "tenant": scope.tenant_id, "ran": True}


class FakeOrganization:
    def __init__(self, chain: dict[str, list[str]] | None = None) -> None:
        self._chain = chain or {}

    def escalation_chain(self, agent_id: str, scope: Scope) -> list[str]:
        return self._chain.get(agent_id, ["human"])
