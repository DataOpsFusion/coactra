"""LangGraphEngine — the ONE working default WorkflowEngine.

Control flow is DELEGATED to LangGraph natives, never re-implemented:
  task     -> a graph node running the registered callable
  branch   -> add_conditional_edges keyed on a CEL-free dict-attribute condition
  approve  -> a node that consults ctx.approver (proceed or stop)
  ask      -> a node that consults ctx.collaborator and records the answer in state
  escalate -> a node that routes ctx.router up ctx.chain to a decider
The compiled artifact is a real langgraph CompiledStateGraph (proven by a conformance
test). __path__ is tracked in state so RunResult can report the steps actually visited.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from coactra.jobs.workflow.runtime.engine import RunContext
from coactra.jobs.workflow.runtime.handlers import Escalation
from coactra.jobs.workflow.domain.models import Procedure, RunResult, Step

TaskFn = Callable[[dict[str, Any]], dict[str, Any]]
_PATH = "__path__"
_STOPPED = "__stopped__"


class LangGraphEngine:
    """Compiles Procedures into LangGraph StateGraphs and runs them."""

    def __init__(self, tasks: dict[str, TaskFn] | None = None) -> None:
        self._tasks = tasks or {}

    # --- node builders ---------------------------------------------------------------

    def _record(self, state: dict[str, Any], step_id: str) -> list[str]:
        return [*state.get(_PATH, []), step_id]

    def _task_node(self, step: Step) -> TaskFn:
        fn = self._tasks.get(step.id, lambda s: s)

        def node(state: dict[str, Any]) -> dict[str, Any]:
            updated = fn(state)
            # Merge over the prior state so a task fn returning a PARTIAL dict never drops
            # keys — correct regardless of whether StateGraph(dict) merges or replaces.
            return {**state, **updated, _PATH: self._record(state, step.id)}

        return node

    def _branch_node(self, step: Step) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, _PATH: self._record(state, step.id)}

        return node

    def _approve_node(self, step: Step, ctx: RunContext) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            ok = ctx.approver.approve(step.id, state)
            return {
                **state,
                _PATH: self._record(state, step.id),
                _STOPPED: not ok,
            }

        return node

    def _ask_node(self, step: Step, ctx: RunContext) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            question = step.question or str(state)
            answer = ctx.collaborator.ask(step.agent or "", question, state)
            answers = {**state.get("answers", {}), step.agent: answer}
            return {**state, "answers": answers, _PATH: self._record(state, step.id)}

        return node

    def _escalate_node(self, step: Step, ctx: RunContext) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            esc = Escalation(reason=step.reason or step.id, state=state)
            decider = ctx.router.route(esc, ctx.chain)
            return {
                **state,
                "decider": decider,
                _PATH: self._record(state, step.id),
            }

        return node

    # --- compilation -----------------------------------------------------------------

    def compile(self, procedure: Procedure, ctx: RunContext):
        graph: StateGraph = StateGraph(dict)
        builders = {
            "task": self._task_node,
            "branch": self._branch_node,
            "approve": lambda s: self._approve_node(s, ctx),
            "ask": lambda s: self._ask_node(s, ctx),
            "escalate": lambda s: self._escalate_node(s, ctx),
        }
        for step in procedure.steps:
            graph.add_node(step.id, builders[step.kind](step))

        graph.add_edge(START, procedure.entry.id)

        for step in procedure.steps:
            if step.kind == "branch":
                graph.add_conditional_edges(
                    step.id,
                    self._branch_selector(step),
                    {True: step.if_true, False: step.if_false},
                )
            elif step.kind == "approve":
                graph.add_conditional_edges(
                    step.id,
                    lambda state: not state.get(_STOPPED, False),
                    {True: step.next or END, False: END},
                )
            else:
                graph.add_edge(step.id, step.next or END)

        return graph.compile()

    @staticmethod
    def _branch_selector(step: Step):
        attr = step.condition

        def select(state: dict[str, Any]) -> bool:
            return bool(state.get(attr))

        return select

    # --- execution -------------------------------------------------------------------

    def run(
        self, procedure: Procedure, state: dict[str, Any], ctx: RunContext
    ) -> RunResult:
        compiled = self.compile(procedure, ctx)
        final = compiled.invoke({**state, _PATH: []})
        path = final.pop(_PATH, [])
        final.pop(_STOPPED, None)
        return RunResult(output=final, path=path)
