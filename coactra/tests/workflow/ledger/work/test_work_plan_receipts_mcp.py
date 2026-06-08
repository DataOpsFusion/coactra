import pytest

from coactra.workflow.ledger import AuditContext, WorkManager, WorkOrder
from coactra.workflow.ledger.adapters import MCPTaskNotTerminalError, MCPTasksAdapter, to_mcp_task
from coactra.workflow.ledger.domain.scope import Scope as WorkScope


def test_plan_execute_inspect_returns_stable_receipt_and_audit_context():
    manager = WorkManager()
    scope = WorkScope(tenant_id="acme", namespace="engineering")
    plan = manager.plan(
        scope=scope,
        title="Deploy website",
        procedure="deploy",
        audit_context=AuditContext(
            trace_id="trace-1",
            agent_id="agent:builder",
            department_id="engineering",
            policy_decision_id="decision-1",
            delegation_chain=["human:ceo", "agent:builder"],
        ),
    )

    receipt = manager.execute(plan)
    same_receipt = manager.execute(plan)
    current = manager.inspect(receipt)

    assert same_receipt.work_order_id == receipt.work_order_id
    assert current.procedure == "deploy"
    event = manager.events(receipt.work_order_id, scope)[0]
    assert event.data["trace_id"] == "trace-1"
    assert event.data["policy_decision_id"] == "decision-1"
    assert event.data["delegation_chain"] == ["human:ceo", "agent:builder"]


def test_mcp_tasks_adapter_maps_work_status_and_enforces_scope():
    manager = WorkManager()
    scope = WorkScope(tenant_id="acme")
    order = manager.submit(WorkOrder(scope=scope, title="Need approval"))
    adapter = MCPTasksAdapter(manager, poll_interval=1000)

    assert to_mcp_task(order).status == "working"
    assert adapter.get(order.id, scope).poll_interval == 1000
    with pytest.raises(MCPTaskNotTerminalError):
        adapter.result(order.id, scope)

    lease = manager.claim(order.id, scope, worker="agent:builder")
    manager.start(lease, scope)
    manager.request_approval(lease, scope, prompt="Ship?")
    assert adapter.get(order.id, scope).status == "input_required"
    assert adapter.get(order.id, scope).status_message == "Ship?"

    cancelled = adapter.cancel(order.id, scope, reason="not now")
    assert cancelled.status == "cancelled"
    assert adapter.result(order.id, scope).status == "cancelled"
