"""Company control-plane primitives.

This module defines the declarative company model a host app can expose through
CLI, HTTP, or MCP tools. The database remains an implementation detail behind an
``OrgStore``.
"""

from __future__ import annotations

from dataclasses import dataclass

from coactra.organization.domain.organization import Organization
from coactra.organization.repository.store import OrgStore
from coactra.organization.service import load_org, save_org

_SENIORITY_RANKS = {
    "intern": 0,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "lead": 5,
    "principal": 6,
    "director": 7,
    "vp": 8,
    "ceo": 9,
}


@dataclass(frozen=True)
class SeniorityLevelSpec:
    name: str
    rank: int


@dataclass(frozen=True)
class RoleSpec:
    id: str
    name: str | None = None
    allowed_tools: tuple[str, ...] = ()
    memory_namespaces: tuple[str, ...] = ()
    approval_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class DepartmentSpec:
    id: str
    name: str
    parent_id: str | None = None
    runtime: str = "procedure"
    manager_agent_id: str | None = None
    allowed_tools: tuple[str, ...] = ()
    memory_namespaces: tuple[str, ...] = ()
    approval_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentSpec:
    id: str
    department_id: str
    role: str
    seniority: str = "senior"
    is_manager: bool = False
    model_tier: str = "default"
    persona_ref: str | None = None
    reports_to: str | None = None


@dataclass(frozen=True)
class CompanySpec:
    tenant_id: str
    name: str
    departments: tuple[DepartmentSpec, ...] = ()
    roles: tuple[RoleSpec, ...] = ()
    seniority_levels: tuple[SeniorityLevelSpec, ...] = ()
    agents: tuple[AgentSpec, ...] = ()

    def validate(self) -> None:
        department_ids = {department.id for department in self.departments}
        if len(department_ids) != len(self.departments):
            raise ValueError("department ids must be unique")
        agent_ids = {agent.id for agent in self.agents}
        if len(agent_ids) != len(self.agents):
            raise ValueError("agent ids must be unique")
        role_ids = {role.id for role in self.roles}
        missing_departments = sorted(
            agent.department_id
            for agent in self.agents
            if agent.department_id not in department_ids
        )
        if missing_departments:
            raise ValueError(
                f"agent references unknown department(s): {missing_departments}"
            )
        missing_parent_ids = sorted(
            department.parent_id
            for department in self.departments
            if department.parent_id is not None
            and department.parent_id not in department_ids
        )
        if missing_parent_ids:
            raise ValueError(
                f"department references unknown parent(s): {missing_parent_ids}"
            )
        missing_roles = sorted(
            agent.role for agent in self.agents if agent.role not in role_ids
        )
        if missing_roles:
            raise ValueError(f"agent references unknown role(s): {missing_roles}")
        unknown_report_targets = sorted(
            agent.reports_to
            for agent in self.agents
            if agent.reports_to is not None and agent.reports_to not in agent_ids
        )
        if unknown_report_targets:
            raise ValueError(
                f"agent references unknown reports_to target(s): {unknown_report_targets}"
            )


@dataclass(frozen=True)
class CompanyBootstrapReport:
    tenant_id: str
    department_count: int
    role_count: int
    seniority_count: int
    agent_count: int
    applied: bool = True
    warnings: tuple[str, ...] = ()


def seniority_rank(name: str, levels: tuple[SeniorityLevelSpec, ...] = ()) -> int:
    for level in levels:
        if level.name == name:
            return level.rank
    return _SENIORITY_RANKS.get(name, 0)


def bootstrap_company(spec: CompanySpec, *, store: OrgStore) -> CompanyBootstrapReport:
    """Apply a company spec to an ``OrgStore`` through domain/service APIs.

    This is intentionally idempotent for departments and agents by name. It projects
    company config into the generic org model:

    * departments become OU nodes;
    * department allowed tools become node grants;
    * agents become members with seats;
    * role tool grants become seat permissions;
    * memory namespaces and approval rules become versioned policy references.
    """

    spec.validate()
    org = load_org(spec.tenant_id, store=store) or Organization.root(
        tenant=spec.tenant_id,
        name=spec.name,
    )
    nodes = {node.name: node for node in org.walk()}
    department_nodes: dict[str, Organization] = {}

    for department in department_order(spec.departments):
        parent = (
            org
            if department.parent_id is None
            else department_nodes[department.parent_id]
        )
        node = nodes.get(department.name)
        if node is None:
            node = parent.add_child(department.name)
            nodes[node.name] = node
        department_nodes[department.id] = node
        for tool in department.allowed_tools:
            node.grant(tool)
        for namespace in department.memory_namespaces:
            org.add_policy_ref(
                f"memory_namespace:{department.id}:{namespace}",
                target=department.id,
            )
        for rule in department.approval_rules:
            org.add_policy_ref(
                f"approval_rule:{department.id}:{rule}",
                target=department.id,
            )

    roles = {role.id: role for role in spec.roles}
    known_members = {member.name for member in org.members(recursive=True)}
    for agent in spec.agents:
        if agent.id in known_members:
            continue
        role = roles[agent.role]
        department = department_nodes[agent.department_id]
        department.hire(
            agent.id,
            role=agent.role,
            permissions=set(role.allowed_tools),
            seniority=seniority_rank(agent.seniority, spec.seniority_levels),
            created_by="coactra.company.bootstrap",
        )

    for role in spec.roles:
        for namespace in role.memory_namespaces:
            org.add_policy_ref(
                f"role_memory_namespace:{role.id}:{namespace}", target=role.id
            )
        for rule in role.approval_rules:
            org.add_policy_ref(f"role_approval_rule:{role.id}:{rule}", target=role.id)

    save_org(org, store=store)
    return CompanyBootstrapReport(
        tenant_id=spec.tenant_id,
        department_count=len(spec.departments),
        role_count=len(spec.roles),
        seniority_count=len(spec.seniority_levels),
        agent_count=len(spec.agents),
    )


def preview_company(spec: CompanySpec) -> CompanyBootstrapReport:
    spec.validate()
    return CompanyBootstrapReport(
        tenant_id=spec.tenant_id,
        department_count=len(spec.departments),
        role_count=len(spec.roles),
        seniority_count=len(spec.seniority_levels),
        agent_count=len(spec.agents),
        applied=False,
    )


def department_order(departments: tuple[DepartmentSpec, ...]) -> list[DepartmentSpec]:
    by_id = {department.id: department for department in departments}
    ordered: list[DepartmentSpec] = []
    visited: set[str] = set()

    def visit(department: DepartmentSpec) -> None:
        if department.id in visited:
            return
        if department.parent_id is not None:
            visit(by_id[department.parent_id])
        visited.add(department.id)
        ordered.append(department)

    for department in departments:
        visit(department)
    return ordered
