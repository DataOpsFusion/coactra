"""Bridge promoted workflow Procedures into the Agent Skill/tool surface.

This module is intentionally adapter-shaped: old coactra.workflow
Procedures stay the source of truth, while agents publish curated Skills and
get replay tools that can call an injected WorkflowEngine.
"""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Iterable
from typing import Any

from coactra.agent.skills import Skill

__all__ = [
    "learned_procedure_skills",
    "learned_procedure_tools",
    "normalize_learned_procedures",
]


def _slug(name: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_").lower()
    return slug or "procedure"


def _is_promoted_version(item: Any) -> bool:
    return hasattr(item, "procedure") and hasattr(item, "version") and hasattr(item, "promoted_by")


def _as_procedure(item: Any, *, allow_unreviewed: bool) -> Any:
    if _is_promoted_version(item):
        return item.procedure
    if allow_unreviewed:
        procedure = getattr(item, "procedure", None)
        return procedure if procedure is not None else item
    raise ValueError(
        "learned procedures must be promoted ProcedureVersion objects; "
        "pass allow_unreviewed_learned=True for explicit local experiments"
    )


def normalize_learned_procedures(learned: Any, *, allow_unreviewed: bool = False) -> list[Any]:
    """Normalize Agent.create(learned=...) values to promoted Procedure objects."""
    if learned is None:
        return []
    if _is_promoted_version(learned):
        return [_as_procedure(learned, allow_unreviewed=allow_unreviewed)]
    if isinstance(learned, Iterable) and not isinstance(learned, (str, bytes, dict)):
        return [_as_procedure(item, allow_unreviewed=allow_unreviewed) for item in learned]
    return [_as_procedure(learned, allow_unreviewed=allow_unreviewed)]


def learned_procedure_skills(procedures: list[Any]) -> list[Skill]:
    """Expose learned Procedures as curated Agent Card skills."""
    skills: list[Skill] = []
    for procedure in procedures:
        name = str(getattr(procedure, "name", "procedure"))
        tags = ["procedure"]
        if getattr(procedure, "is_induced", False):
            tags.append("learned")
        skills.append(
            Skill(
                id=f"procedure.{_slug(name)}",
                description=f"Replay procedure: {name}",
                tags=tuple(tags),
            )
        )
    return skills


def _state_from(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return {"input": value}


def _run_payload(procedure: Any, run: Any) -> str:
    status = getattr(run, "status", "completed")
    state = getattr(run, "state", None)
    result = getattr(run, "result", None)
    if state is None and result is not None:
        state = getattr(result, "output", None)
    payload = {
        "procedure": getattr(procedure, "name", "procedure"),
        "status": str(status),
        "state": state or {},
    }
    return json.dumps(payload, sort_keys=True)


def learned_procedure_tools(
    procedures: list[Any],
    *,
    engine: Any | None,
    tenant: str | None,
    scope: Any | None = None,
) -> list[Any]:
    """Build replay tools for learned Procedures.

    The generated tools call an injected durable WorkflowEngine when one is
    supplied. Without an engine they fail honestly with a short configuration
    message instead of simulating a workflow run.
    """
    tools: list[Any] = []

    for procedure in procedures:
        name = str(getattr(procedure, "name", "procedure"))
        tool_name = f"replay_{_slug(name)}"

        async def _tool(
            state: dict[str, Any] | str | None = None,
            *,
            thread_id: str | None = None,
            _procedure: Any = procedure,
        ) -> str:
            if engine is None:
                return (
                    f"procedure engine not configured for {_procedure.name!r}; "
                    "pass procedure_engine= to Agent.create"
                )

            from coactra.workflow import RunContext, Scope  # noqa: PLC0415

            run_scope = scope if scope is not None else Scope(tenant_id=tenant or "default")
            ctx = RunContext(scope=run_scope)
            initial_state = _state_from(state)

            if hasattr(engine, "start"):
                run = engine.start(_procedure, initial_state, ctx, thread_id=thread_id)
                if inspect.isawaitable(run):
                    run = await run
                return _run_payload(_procedure, run)

            if hasattr(engine, "run"):
                run = engine.run(_procedure, initial_state, ctx)
                if inspect.isawaitable(run):
                    run = await run
                return _run_payload(_procedure, run)

            raise TypeError("procedure_engine must implement start(...) or run(...)")

        _tool.__name__ = tool_name
        _tool.__qualname__ = tool_name
        tools.append(_tool)

    return tools
