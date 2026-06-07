"""Durable LangGraph workflow backend.

This backend is the generic, reusable counterpart to host-specific workflow
runtimes. It owns LangGraph compilation, checkpointed start/resume, interrupts,
branch/loop/parallel control flow, templating, and simple done criteria. It does
not know about MCP, Keycloak, Redis, CouchDB, or any deployment-specific
registry. Hosts inject those pieces through small callables/ports.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from collections.abc import Callable
from typing import Annotated, Any

import celpy
from jinja2.sandbox import SandboxedEnvironment
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt
from typing_extensions import TypedDict

from coactra.workflow.domain.models import Procedure, RunResult
from coactra.workflow.runtime.durable import (
    WorkflowInterrupt,
    WorkflowNotResumableError,
    WorkflowRun,
    WorkflowRunStatus,
)
from coactra.workflow.runtime.engine import RunContext
from coactra.workflow.runtime.handlers import Escalation
from coactra.workflow.runtime.capabilities import (
    CapabilityRegistry,
    validate_tool_call,
    validate_workflow_capabilities,
)
from coactra.workflow.runtime.tools import ToolInvoker
from coactra.workflow.runtime.verification import (
    VerificationResult,
    is_error_like,
    is_missing,
    is_successful_value,
    read_state_path,
)

log = logging.getLogger(__name__)

_JINJA = SandboxedEnvironment()
_CEL_ENV = celpy.Environment()
_DEFAULT_MAX_FANOUT = 100


def merge_data(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> dict[str, Any]:
    out = dict(left or {})
    out.update(right or {})
    return out


class WFState(TypedDict):
    data: Annotated[dict[str, Any], merge_data]


class CELError(Exception):
    """Raised when a CEL expression cannot be evaluated."""


class ApprovalDenied(Exception):
    """Raised when an operator denies a red-tier action on resume."""


def evaluate_cel(expr: str, data: dict[str, Any]) -> bool:
    """Evaluate a CEL expression with workflow data bound as ``state``."""
    try:
        ast = _CEL_ENV.compile(expr)
        program = _CEL_ENV.program(ast)
        result = program.evaluate({"state": celpy.json_to_cel(data)})
        return bool(result)
    except Exception as exc:  # celpy raises several internal exception types.
        raise CELError(f"CEL eval failed for {expr!r}: {exc}") from exc


def evaluate_collection(expr: str, data: dict[str, Any]) -> list[Any]:
    """Evaluate a CEL expression expected to resolve to a collection."""
    try:
        ast = _CEL_ENV.compile(expr)
        program = _CEL_ENV.program(ast)
        result = program.evaluate({"state": celpy.json_to_cel(data)})
        return list(result)
    except Exception as exc:
        raise CELError(f"CEL collection eval failed for {expr!r}: {exc}") from exc


def render_value(value: Any, state: dict[str, Any]) -> Any:
    """Render strings through sandboxed Jinja while preserving containers."""
    if isinstance(value, str):
        return _JINJA.from_string(value).render(**state)
    if isinstance(value, list):
        return [render_value(v, state) for v in value]
    if isinstance(value, dict):
        return {k: render_value(v, state) for k, v in value.items()}
    return value


def _result_key(node: dict[str, Any]) -> str:
    return node.get("store_as") or f"{node['id'].replace('-', '_')}_result"


def _requires_approval(node: dict[str, Any]) -> bool:
    return str(node.get("tier", "")).strip().lower() == "red"


def _decision_denied(decision: Any) -> bool:
    if isinstance(decision, bool):
        return decision is False
    if isinstance(decision, str):
        return decision.strip().lower() in {
            "deny",
            "denied",
            "reject",
            "rejected",
            "no",
            "false",
        }
    if isinstance(decision, dict):
        if decision.get("approved") is False:
            return True
        return str(decision.get("decision", "")).strip().lower() in {
            "deny",
            "denied",
            "reject",
            "rejected",
            "no",
        }
    return False


def _gate_red_tier(node: dict[str, Any], action: str, params: Any) -> None:
    """Interrupt before red-tier side effects and interpret the resume value."""
    if not _requires_approval(node):
        return
    decision = interrupt(
        {
            "node": node["id"],
            "tier": "red",
            "action": action,
            "params": params,
            "approval_required": True,
        }
    )
    if _decision_denied(decision):
        raise ApprovalDenied(
            f"red-tier node {node['id']!r} ({action}) denied by operator"
        )


def make_tool_node(
    node: dict[str, Any],
    tool_invoker: ToolInvoker | None,
    capability_registry: CapabilityRegistry | None = None,
) -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        if tool_invoker is None:
            raise ValueError(f"tool node {node['id']} requires a tool_invoker")
        data = state["data"]
        params = render_value(node.get("inputs", {}), data)
        if capability_registry is not None:
            validate_tool_call(
                capability_registry,
                server=node["target"],
                tool=node["tool"],
                params=params,
                node_id=node["id"],
            )
        _gate_red_tier(node, f"call {node.get('target')}.{node.get('tool')}", params)
        result = await tool_invoker.call(
            server=node["target"],
            tool=node["tool"],
            params=params,
        )
        return {"data": {_result_key(node): result}}

    return _node


def make_python_node(node: dict[str, Any], registry: dict[str, Callable]) -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        data = state["data"]
        _gate_red_tier(
            node, f"python:{node['function']}", {"function": node["function"]}
        )
        fn = registry[node["function"]]
        result = fn(data)
        if inspect.isawaitable(result):
            result = await result
        return {"data": result if isinstance(result, dict) else {}}

    return _node


def make_prompt_node(node: dict[str, Any], llm: Any) -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        if llm is None:
            raise ValueError(f"prompt node {node['id']} requires an llm")
        data = state["data"]
        rendered = render_value(node.get("prompt", ""), data)
        response = await llm.ainvoke(rendered)
        content = getattr(response, "content", str(response))
        return {"data": {_result_key(node): content}}

    return _node


def make_human_node(node: dict[str, Any]) -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        data = state["data"]
        prompt = render_value(node.get("prompt", ""), data)
        decision = interrupt(
            {
                "node": node["id"],
                "prompt": prompt,
                "tier": node.get("tier", "red"),
            }
        )
        return {"data": {f"{node['id'].replace('-', '_')}_decision": decision}}

    return _node


def make_branch_node() -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        return {"data": {}}

    return _node


def make_ask_node(node: dict[str, Any], ctx: RunContext | None) -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        if ctx is None:
            raise ValueError(f"ask node {node['id']} requires a RunContext")
        data = state["data"]
        question = render_value(node.get("question") or str(data), data)
        answer = ctx.collaborator.ask(node.get("agent", ""), question, data)
        if inspect.isawaitable(answer):
            answer = await answer
        answers = {**data.get("answers", {}), node.get("agent", ""): answer}
        return {"data": {_result_key(node): answer, "answers": answers}}

    return _node


def make_escalate_node(node: dict[str, Any], ctx: RunContext | None) -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        if ctx is None:
            raise ValueError(f"escalate node {node['id']} requires a RunContext")
        data = state["data"]
        escalation = Escalation(reason=node.get("reason") or node["id"], state=data)
        decider = ctx.router.route(escalation, ctx.chain)
        if inspect.isawaitable(decider):
            decider = await decider
        return {"data": {_result_key(node): decider, "decider": decider}}

    return _node


def make_sub_procedure_node(
    node: dict[str, Any],
    *,
    tool_invoker: ToolInvoker | None,
    llm: Any,
    python_registry: dict[str, Callable],
    procedure_resolver: Callable,
    ctx: RunContext | None,
    node_timeout: float | None = None,
    workflow_timeout: float | None = None,
    capability_registry: CapabilityRegistry | None = None,
    checkpointer: Any = None,
    parent_thread_id: str | None = None,
) -> Callable:
    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        child = await procedure_resolver(node["procedure"], node.get("version"))
        params = render_value(node.get("params", {}), state["data"])
        _gate_red_tier(node, f"sub-procedure:{node['procedure']}", params)
        # Run the child on the PARENT's checkpointer under a child-scoped thread so
        # its progress is durably checkpointed (no node re-execution on resume). If
        # the child hits a human gate it must pause the PARENT too — re-raise the
        # child interrupt here so the whole nesting is resumable through the parent
        # checkpointer instead of being swallowed by a throwaway MemorySaver.
        child_thread = f"{parent_thread_id or node['procedure']}::{node['id']}"
        decision: Any = None
        while True:
            child_state = await run_workflow(
                child,
                params=params,
                tool_invoker=tool_invoker,
                llm=llm,
                python_registry=python_registry,
                procedure_resolver=procedure_resolver,
                ctx=ctx,
                node_timeout=node_timeout,
                workflow_timeout=workflow_timeout,
                capability_registry=capability_registry,
                checkpointer=checkpointer,
                thread_id=child_thread,
                resume=decision,
            )
            if not child_state.get("_awaiting_human"):
                return {"data": {_result_key(node): child_state}}
            decision = interrupt(child_state["_interrupt"])

    return _node


def make_loop_dispatch(node: dict[str, Any]) -> Callable:
    over_expr = node["iterate_over"]
    item_node = node["item_node"]
    as_key = node.get("as", "item")
    cap = node.get("max_fanout", _DEFAULT_MAX_FANOUT)

    def _dispatch(state: dict[str, Any]) -> list[Send]:
        data = state["data"]
        try:
            items = list(evaluate_collection(over_expr, data))
        except CELError as exc:
            log.warning(
                "loop_cel_error",
                extra={"node": node.get("id"), "expr": over_expr, "error": str(exc)},
            )
            items = []
        if isinstance(cap, int) and cap >= 0 and len(items) > cap:
            log.warning(
                "loop_fanout_truncated",
                extra={"node": node.get("id"), "total": len(items), "cap": cap},
            )
            items = items[:cap]
        return [Send(item_node, {"data": {**data, as_key: item}}) for item in items]

    return _dispatch


def _with_timeout(node_fn: Callable, nid: str, timeout: float | None) -> Callable:
    """Wrap a node coroutine in a total-wall-clock deadline.

    A slow/hung tool or LLM node would otherwise stall the whole run forever
    (an httpx per-operation timeout does not bound total duration over SSE).
    On expiry the node raises TimeoutError, which the host's self-heal/escalate
    path treats like any node failure. A ``None`` or non-positive ``timeout``
    disables it (no-op) — the opt-out for legitimately long-running nodes.
    """
    if not timeout or timeout <= 0:
        return node_fn

    async def _wrapped(state: dict[str, Any]) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(node_fn(state), timeout)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"node {nid!r} exceeded {timeout}s") from exc

    return _wrapped


def build_graph(
    workflow: dict[str, Any],
    *,
    tool_invoker: ToolInvoker | None = None,
    llm: Any = None,
    python_registry: dict[str, Callable] | None = None,
    procedure_resolver: Callable | None = None,
    ctx: RunContext | None = None,
    node_timeout: float | None = None,
    workflow_timeout: float | None = None,
    capability_registry: CapabilityRegistry | None = None,
    checkpointer: Any = None,
    parent_thread_id: str | None = None,
) -> StateGraph:
    """Compile a declarative workflow document into a LangGraph builder.

    ``node_timeout`` (seconds) bounds each tool/prompt node's total execution;
    a node may override it with its own ``timeout`` field. ``None`` (default)
    leaves nodes unbounded, preserving prior behavior.
    """
    python_registry = python_registry or {}
    nodes = {n["id"]: n for n in workflow["nodes"]}
    if capability_registry is not None:
        validate_workflow_capabilities(workflow, capability_registry)

    for edge in workflow.get("edges", []):
        if edge["from"] not in nodes or edge["to"] not in nodes:
            raise ValueError(f"edge references unknown node: {edge}")

    builder: StateGraph = StateGraph(WFState)
    branch_ids: set[str] = set()
    parallel_ids: set[str] = set()
    loop_ids: set[str] = set()

    for node in workflow["nodes"]:
        nid, ntype = node["id"], node["type"]
        _nt = node.get("timeout", node_timeout)
        if _nt is None and ntype == "tool" and capability_registry is not None:
            capability = capability_registry.get(node["target"], node["tool"])
            if capability is not None:
                _nt = capability.timeout_seconds
        if ntype == "tool":
            builder.add_node(
                nid,
                _with_timeout(
                    make_tool_node(node, tool_invoker, capability_registry),
                    nid,
                    _nt,
                ),
            )
        elif ntype == "python":
            if node["function"] not in python_registry:
                raise ValueError(
                    f"python node {nid!r}: function {node['function']!r} not in registry"
                )
            builder.add_node(nid, make_python_node(node, python_registry))
        elif ntype == "prompt":
            builder.add_node(nid, _with_timeout(make_prompt_node(node, llm), nid, _nt))
        elif ntype == "human":
            builder.add_node(nid, make_human_node(node))
        elif ntype == "ask":
            builder.add_node(nid, make_ask_node(node, ctx))
        elif ntype == "escalate":
            builder.add_node(nid, make_escalate_node(node, ctx))
        elif ntype == "branch":
            branch_ids.add(nid)
            builder.add_node(nid, make_branch_node())
        elif ntype == "parallel":
            parallel_ids.add(nid)
            builder.add_node(nid, make_branch_node())
        elif ntype == "loop":
            loop_ids.add(nid)
            builder.add_node(nid, make_branch_node())
        elif ntype == "sub-procedure":
            if procedure_resolver is None:
                raise ValueError(
                    f"sub-procedure node {nid!r} requires a procedure_resolver"
                )
            builder.add_node(
                nid,
                make_sub_procedure_node(
                    node,
                    tool_invoker=tool_invoker,
                    llm=llm,
                    python_registry=python_registry,
                    procedure_resolver=procedure_resolver,
                    ctx=ctx,
                    node_timeout=node_timeout,
                    workflow_timeout=workflow_timeout,
                    capability_registry=capability_registry,
                    checkpointer=checkpointer,
                    parent_thread_id=parent_thread_id,
                ),
            )
        else:
            raise ValueError(f"unsupported node type: {ntype!r}")

    incoming: dict[str, int] = {n["id"]: 0 for n in workflow["nodes"]}
    for edge in workflow.get("edges", []):
        incoming[edge["to"]] += 1
    for node in workflow["nodes"]:
        if node["type"] == "branch":
            for target in (node.get("then"), node.get("else")):
                if target:
                    incoming[target] = incoming.get(target, 0) + 1
        elif node["type"] == "parallel":
            for branch in node.get("branches", []):
                incoming[branch] = incoming.get(branch, 0) + 1
        elif node["type"] == "loop":
            item = node.get("item_node")
            if item:
                incoming[item] = incoming.get(item, 0) + 1

    roots = [node_id for node_id, count in incoming.items() if count == 0]
    if not roots:
        raise ValueError("workflow has no root node (every node has an incoming edge)")
    for root in roots:
        builder.add_edge(START, root)

    has_outgoing: set[str] = set()
    for edge in workflow.get("edges", []):
        if (
            edge["from"] in branch_ids
            or edge["from"] in parallel_ids
            or edge["from"] in loop_ids
        ):
            continue
        builder.add_edge(edge["from"], edge["to"])
        has_outgoing.add(edge["from"])

    out_targets = {e["from"]: e["to"] for e in workflow.get("edges", [])}
    for node in workflow["nodes"]:
        if node["type"] != "parallel":
            continue
        join_target = out_targets.get(node["id"])
        for branch in node.get("branches", []):
            if branch not in nodes:
                raise ValueError(f"parallel {node['id']!r} branch {branch!r} unknown")
            if branch in out_targets:
                raise ValueError(
                    f"parallel {node['id']!r} branch {branch!r} must be a single node "
                    f"(no outgoing edge); use a sub-procedure for multi-step branches"
                )
            builder.add_edge(node["id"], branch)
            if join_target:
                builder.add_edge(branch, join_target)
            has_outgoing.add(branch)
        has_outgoing.add(node["id"])

    for node in workflow["nodes"]:
        if node["type"] != "loop":
            continue
        item_node = node["item_node"]
        if item_node not in nodes:
            raise ValueError(f"loop {node['id']!r} item_node {item_node!r} unknown")
        join_target = out_targets.get(node["id"])
        builder.add_conditional_edges(node["id"], make_loop_dispatch(node), [item_node])
        if join_target:
            builder.add_edge(item_node, join_target)
        has_outgoing.add(node["id"])
        has_outgoing.add(item_node)

    for node in workflow["nodes"]:
        if node["type"] != "branch":
            continue
        then_target = node.get("then")
        else_target = node.get("else")
        if_expr = node.get("if")
        if not (then_target and else_target and if_expr):
            raise ValueError(f"branch node {node['id']!r} requires if + then + else")

        def _make_router(expr: str, on_true: str, on_false: str):
            def _router(state: dict[str, Any]) -> str:
                try:
                    return on_true if evaluate_cel(expr, state["data"]) else on_false
                except CELError as exc:
                    log.warning(
                        "branch_cel_error", extra={"expr": expr, "error": str(exc)}
                    )
                    return on_false

            return _router

        builder.add_conditional_edges(
            node["id"],
            _make_router(if_expr, then_target, else_target),
            {then_target: then_target, else_target: else_target},
        )
        has_outgoing.add(node["id"])

    for node in workflow["nodes"]:
        if node["id"] not in has_outgoing and node["type"] != "branch":
            builder.add_edge(node["id"], END)

    return builder


def _seed_params(workflow: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    seeded: dict[str, Any] = {}
    for name, spec in (workflow.get("parameters") or {}).items():
        if name in params:
            seeded[name] = params[name]
        elif isinstance(spec, dict) and "default" in spec:
            seeded[name] = spec["default"]
        else:
            seeded[name] = None
    for key, value in params.items():
        seeded.setdefault(key, value)
    return seeded


async def check_done_criteria(
    criteria: list[dict[str, Any]],
    state_data: dict[str, Any],
    *,
    tool_invoker: ToolInvoker | None = None,
) -> tuple[bool, list[str]]:
    """Compatibility wrapper returning the historical boolean/failures shape."""
    result = await verify_done_criteria(criteria, state_data, tool_invoker=tool_invoker)
    return (result.passed, result.failures)


async def verify_done_criteria(
    criteria: list[dict[str, Any]],
    state_data: dict[str, Any],
    *,
    tool_invoker: ToolInvoker | None = None,
) -> VerificationResult:
    """Run structured done criteria against final workflow state."""
    failures: list[str] = []
    evidence: dict[str, Any] = {}
    for criterion in criteria or []:
        ctype = criterion.get("type")
        if ctype == "cel":
            try:
                if not evaluate_cel(criterion["expression"], state_data):
                    failures.append(f"cel failed: {criterion['expression']}")
                else:
                    evidence[criterion["expression"]] = True
            except CELError as exc:
                failures.append(f"cel error: {exc}")
        elif ctype == "exists":
            path = str(criterion.get("path") or criterion.get("key") or "")
            value = read_state_path(state_data, path)
            if not path or is_missing(value) or value is None:
                failures.append(f"missing state path: {path!r}")
            else:
                evidence[path] = value
        elif ctype == "success":
            path = str(criterion.get("path") or criterion.get("key") or "")
            value = read_state_path(state_data, path)
            if not is_successful_value(value):
                failures.append(f"state path is not successful: {path!r}")
            else:
                evidence[path] = value
        elif ctype == "not_error":
            path = str(criterion.get("path") or criterion.get("key") or "")
            value = read_state_path(state_data, path)
            if is_missing(value):
                failures.append(f"missing state path: {path!r}")
            elif is_error_like(value):
                failures.append(f"state path is error-like: {path!r}")
            else:
                evidence[path] = value
        elif ctype == "equals":
            path = str(criterion.get("path") or criterion.get("key") or "")
            value = read_state_path(state_data, path)
            expected = criterion.get("value")
            if value != expected:
                failures.append(f"{path!r}: expected {expected!r}, got {value!r}")
            else:
                evidence[path] = value
        elif ctype == "tool":
            if tool_invoker is None:
                failures.append(f"tool criterion needs tool_invoker: {criterion.get('tool')}")
                continue
            params = render_value(criterion.get("inputs", {}), state_data)
            result = await tool_invoker.call(
                server=criterion["target"],
                tool=criterion["tool"],
                params=params,
            )
            if not isinstance(result, dict):
                failures.append(f"{criterion['tool']}: result is not an object")
                continue
            evidence[str(criterion.get("tool"))] = result
            for key, want in (criterion.get("expect") or {}).items():
                if result.get(key) != want:
                    failures.append(
                        f"{criterion['tool']}: expected {key}={want!r}, got {result.get(key)!r}"
                    )
        else:
            failures.append(f"unknown criterion type: {ctype!r}")
    return VerificationResult(
        status="passed" if not failures else "failed",
        reason="all criteria passed" if not failures else "one or more criteria failed",
        failures=failures,
        evidence=evidence,
    )


def _pending_interrupt(snapshot: Any) -> Any:
    """Best-effort extraction of the first pending interrupt value from a paused
    LangGraph state snapshot (``aget_state``). Returns ``{}`` if none is found."""
    for task in getattr(snapshot, "tasks", ()) or ():
        for itr in getattr(task, "interrupts", ()) or ():
            return getattr(itr, "value", itr)
    return {}


async def run_workflow(
    workflow: dict[str, Any],
    *,
    params: dict[str, Any],
    tool_invoker: ToolInvoker | None = None,
    llm: Any = None,
    python_registry: dict[str, Callable] | None = None,
    checkpointer: Any = None,
    thread_id: str | None = None,
    resume: Any = None,
    procedure_resolver: Callable | None = None,
    builder: Any = None,
    ctx: RunContext | None = None,
    node_timeout: float | None = None,
    workflow_timeout: float | None = None,
    capability_registry: CapabilityRegistry | None = None,
) -> dict[str, Any]:
    """Compile and run a workflow document through LangGraph.

    Supplying a durable LangGraph checkpointer makes interrupts resumable across
    process restarts. Without one, ``MemorySaver`` is used for tests and local
    run-to-completion flows only.
    """
    for name, spec in (workflow.get("parameters") or {}).items():
        if isinstance(spec, dict) and spec.get("required") and name not in params:
            raise ValueError(
                f"workflow {workflow['name']!r} requires parameter {name!r}"
            )

    # Resolve the checkpointer once and share the SAME instance with any child
    # sub-procedures (threaded via build_graph) so a child's human gate is durably
    # checkpointed and resumable through this parent's checkpointer.
    cp = checkpointer or MemorySaver()
    effective_thread = thread_id or workflow["name"]
    if builder is None:
        builder = build_graph(
            workflow,
            tool_invoker=tool_invoker,
            llm=llm,
            python_registry=python_registry or {},
            procedure_resolver=procedure_resolver,
            ctx=ctx,
            node_timeout=node_timeout,
            workflow_timeout=workflow_timeout,
            capability_registry=capability_registry,
            checkpointer=cp,
            parent_thread_id=effective_thread,
        )
    graph = builder.compile(checkpointer=cp)
    config = {"configurable": {"thread_id": effective_thread}}

    if resume is not None:
        invoke = graph.ainvoke(Command(resume=resume), config)
    else:
        # If this thread is already paused at an interrupt, re-seeding it would
        # restart the run and re-execute completed nodes (re-firing tool side
        # effects). Return the pending interrupt instead, so a re-entrant caller
        # — e.g. a parent sub-procedure node re-executing on resume — observes the
        # paused child without re-running it.
        existing = await graph.aget_state(config)
        if existing.next:
            data = dict((existing.values or {}).get("data", {}))
            data["_awaiting_human"] = True
            data["_interrupt"] = _pending_interrupt(existing)
            return data
        invoke = graph.ainvoke({"data": _seed_params(workflow, params)}, config)
    try:
        if workflow_timeout and workflow_timeout > 0:
            result = await asyncio.wait_for(invoke, workflow_timeout)
        else:
            result = await invoke
    except asyncio.TimeoutError as exc:
        raise TimeoutError(f"workflow {workflow['name']!r} exceeded {workflow_timeout}s") from exc

    data = dict(result.get("data", {}))
    interrupts = result.get("__interrupt__")
    if interrupts:
        first = interrupts[0]
        data["_awaiting_human"] = True
        data["_interrupt"] = getattr(first, "value", first)
        return data

    criteria = workflow.get("done_criteria")
    if criteria:
        verification = await verify_done_criteria(
            criteria, data, tool_invoker=tool_invoker
        )
        data["_verified"] = verification.passed
        data["_verification"] = verification.model_dump()
        if not verification.passed:
            data["_verify_failures"] = verification.failures
    return data


def document_from_procedure(procedure: Procedure) -> dict[str, Any]:
    """Convert Coactra's portable Procedure model into a workflow document."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for step in procedure.steps:
        if step.kind == "task":
            node = {"id": step.id, "type": "python", "function": step.id}
        elif step.kind == "branch":
            node = {
                "id": step.id,
                "type": "branch",
                "if": f"state.{step.condition}",
                "then": step.if_true,
                "else": step.if_false,
            }
        elif step.kind == "approve":
            node = {
                "id": step.id,
                "type": "human",
                "tier": "red",
                "prompt": f"Approve step {step.id!r}?",
            }
        elif step.kind == "ask":
            node = {
                "id": step.id,
                "type": "ask",
                "agent": step.agent,
                "question": step.question,
            }
        elif step.kind == "escalate":
            node = {"id": step.id, "type": "escalate", "reason": step.reason}
        else:
            raise ValueError(f"unsupported procedure step kind: {step.kind!r}")
        nodes.append(node)
        if step.kind != "branch" and step.next is not None:
            edges.append({"from": step.id, "to": step.next})
    return {"name": procedure.name, "version": "1.0", "nodes": nodes, "edges": edges}


def _scoped_thread_id(ctx: RunContext, thread_id: str | None) -> str:
    prefix = f"{ctx.scope.tenant_id}:"
    raw = thread_id or uuid.uuid4().hex
    return raw if raw.startswith(prefix) else f"{prefix}{raw}"


def _snapshot(thread_id: str, state: dict[str, Any]) -> WorkflowRun:
    if state.get("_awaiting_human"):
        raw = state.get("_interrupt") or {}
        if not isinstance(raw, dict):
            raw = {"value": raw}
        step_id = str(raw.get("node") or raw.get("step_id") or "workflow")
        prompt = str(
            raw.get("prompt") or raw.get("action") or "operator approval required"
        )
        return WorkflowRun(
            thread_id=thread_id,
            status=WorkflowRunStatus.interrupted,
            interrupt=WorkflowInterrupt(
                kind="approval",
                step_id=step_id,
                prompt=prompt,
                metadata=raw,
            ),
            state=state,
        )
    return WorkflowRun(
        thread_id=thread_id,
        status=WorkflowRunStatus.completed,
        result=RunResult(output=state, path=[]),
        state=state,
    )


class DurableLangGraphEngine:
    """Generic checkpointed LangGraph implementation of the WorkflowEngine SPI."""

    satisfies = "WorkflowEngine"

    def __init__(
        self,
        *,
        tool_invoker: ToolInvoker | None = None,
        llm: Any = None,
        python_registry: dict[str, Callable] | None = None,
        checkpointer: Any = None,
        procedure_resolver: Callable | None = None,
        capability_registry: CapabilityRegistry | None = None,
        node_timeout: float | None = None,
        workflow_timeout: float | None = None,
    ) -> None:
        self._tool_invoker = tool_invoker
        self._llm = llm
        self._registry = python_registry or {}
        self._checkpointer = checkpointer
        self._procedure_resolver = procedure_resolver
        self._capability_registry = capability_registry
        self._node_timeout = node_timeout
        self._workflow_timeout = workflow_timeout
        self._procedure_by_thread: dict[str, Procedure] = {}

    async def run_document(
        self,
        doc: dict[str, Any],
        *,
        params: dict[str, Any],
        thread_id: str | None = None,
        resume: Any = None,
        ctx: RunContext | None = None,
        node_timeout: float | None = None,
        workflow_timeout: float | None = None,
    ) -> dict[str, Any]:
        return await run_workflow(
            doc,
            params=params,
            tool_invoker=self._tool_invoker,
            llm=self._llm,
            python_registry=self._registry,
            checkpointer=self._checkpointer,
            thread_id=thread_id,
            resume=resume,
            procedure_resolver=self._procedure_resolver,
            ctx=ctx,
            node_timeout=node_timeout if node_timeout is not None else self._node_timeout,
            workflow_timeout=(
                workflow_timeout
                if workflow_timeout is not None
                else self._workflow_timeout
            ),
            capability_registry=self._capability_registry,
        )

    async def start(
        self,
        procedure: Procedure,
        state: dict[str, Any],
        ctx: RunContext,
        *,
        thread_id: str | None = None,
    ) -> WorkflowRun:
        scoped_thread = _scoped_thread_id(ctx, thread_id)
        self._procedure_by_thread[scoped_thread] = procedure
        result = await self.run_document(
            document_from_procedure(procedure),
            params=state,
            thread_id=scoped_thread,
            ctx=ctx,
        )
        return _snapshot(scoped_thread, result)

    async def resume(
        self,
        thread_id: str,
        ctx: RunContext,
        *,
        procedure: Procedure | None = None,
        decision: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        scoped_thread = _scoped_thread_id(ctx, thread_id)
        if scoped_thread != thread_id:
            raise ValueError("workflow thread belongs to a different tenant")
        selected = procedure or self._procedure_by_thread.get(thread_id)
        if selected is None:
            raise WorkflowNotResumableError(
                "resume requires the persisted procedure after a process restart"
            )
        self._procedure_by_thread[thread_id] = selected
        result = await self.run_document(
            document_from_procedure(selected),
            params=state or {},
            thread_id=thread_id,
            resume=decision,
            ctx=ctx,
        )
        return _snapshot(thread_id, result)
