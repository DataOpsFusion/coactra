"""Small durable workflow engine for Coactra Procedure runs.

This module used to contain a large LangGraph document interpreter. Coactra's
core now keeps the stable durable boundary and a tiny in-process implementation;
external graph runtimes should live behind adapters instead of in the core path.
"""

from __future__ import annotations

import uuid
from typing import Any

from coactra.workflow.domain.models import Procedure, RunResult
from coactra.workflow.runtime.durable import (
    WorkflowEngine,
    WorkflowInterrupt,
    WorkflowRun,
    WorkflowRunStatus,
)
from coactra.workflow.runtime.engine import RunContext


class DurableLangGraphEngine:
    """Minimal resumable Procedure engine implementing ``WorkflowEngine``.

    The public name is kept for the alpha runtime selector, but the implementation
    is deliberately small: linear Procedure execution, human approval interrupts,
    task callbacks, and collaborator asks. Hosts that need full LangGraph document
    semantics should provide their own WorkflowEngine adapter.
    """

    def __init__(
        self,
        *,
        python_registry: dict[str, Any] | None = None,
        tasks: dict[str, Any] | None = None,
        checkpointer: Any | None = None,
        **_: Any,
    ) -> None:
        self._tasks = {**(python_registry or {}), **(tasks or {})}
        self._runs: dict[str, WorkflowRun] = {}
        self._procedures: dict[str, Procedure] = {}
        self._checkpointer = checkpointer

    async def start(
        self,
        procedure: Procedure,
        state: dict[str, Any],
        ctx: RunContext,
        *,
        thread_id: str | None = None,
    ) -> WorkflowRun:
        tid = self._thread_id(ctx, thread_id)
        existing = self._runs.get(tid)
        if existing is not None:
            return existing
        self._procedures[tid] = procedure
        run = await self._execute(procedure, dict(state), ctx, tid)
        self._runs[tid] = run
        return run

    async def resume(
        self,
        thread_id: str,
        ctx: RunContext,
        *,
        procedure: Procedure | None = None,
        decision: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        procedure = procedure or self._procedures.get(thread_id)
        if procedure is None:
            raise ValueError(f"unknown workflow thread: {thread_id}")
        prior = self._runs.get(thread_id)
        merged = dict(prior.state if prior is not None else {})
        merged.update(state or {})
        interrupt = prior.interrupt if prior is not None else None
        if interrupt is not None:
            approved = bool((decision or {}).get("approved", False))
            merged[f"{interrupt.step_id}_decision"] = {"approved": approved}
            if not approved:
                run = WorkflowRun(
                    thread_id=thread_id,
                    status=WorkflowRunStatus.completed,
                    result=RunResult(output=merged, path=merged.get("__path__", [])),
                    state=merged,
                )
                self._runs[thread_id] = run
                return run
        run = await self._execute(procedure, merged, ctx, thread_id)
        self._runs[thread_id] = run
        return run

    @staticmethod
    def _thread_id(ctx: RunContext, thread_id: str | None) -> str:
        raw = thread_id or uuid.uuid4().hex
        if ":" in raw:
            return raw
        return f"{ctx.scope.tenant_id}:{raw}"

    async def _execute(
        self, procedure: Procedure, state: dict[str, Any], ctx: RunContext, thread_id: str
    ) -> WorkflowRun:
        steps = {step.id: step for step in procedure.steps}
        current = procedure.entry.id
        path = list(state.get("__path__", []))

        while current:
            step = steps[current]
            if step.id not in path:
                path.append(step.id)
            state["__path__"] = path

            if step.kind == "approve":
                key = f"{step.id}_decision"
                if key not in state:
                    return WorkflowRun(
                        thread_id=thread_id,
                        status=WorkflowRunStatus.interrupted,
                        interrupt=WorkflowInterrupt(
                            kind="approval",
                            step_id=step.id,
                            prompt=step.reason or f"Approve {step.id}?",
                        ),
                        state=state,
                    )
                if not bool(state[key].get("approved", False)):
                    break
                current = step.next
                continue

            if step.kind == "ask":
                question = step.question or step.id
                answer = ctx.collaborator.ask(step.agent or "", question, state)
                state[f"{step.id}_result"] = answer
                current = step.next
                continue

            if step.kind == "task":
                fn = self._tasks.get(step.id)
                if fn is not None:
                    update = fn(state)
                    if update is not None:
                        state.update(update)
                current = step.next
                continue

            if step.kind == "branch":
                current = step.if_true if state.get(step.condition or "") else step.if_false
                continue

            current = step.next

        output = {k: v for k, v in state.items() if k != "__path__"}
        return WorkflowRun(
            thread_id=thread_id,
            status=WorkflowRunStatus.completed,
            result=RunResult(output=output, path=path),
            state=output,
        )


assert isinstance(DurableLangGraphEngine(), WorkflowEngine)
