"""Team-first coordination facade.

Team is the alpha assembly and execution root for Coactra applications. It owns
agent, skill, workflow, and model-routing catalogs; routes capability-based work;
and carries canonical scope and policy for its members.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from coactra.agent import Agent
from coactra.agent.skills import Skill
from coactra.agent.spec import AgentSpec
from coactra.model import ModelProfile, ModelResolver, ModelRoute
from coactra.policy import DecisionOutcome, Policy, PolicyRequest
from coactra.policy import permissive as _permissive_policy
from coactra.scope import Scope

__all__ = ["Team"]


def _has_required_tags(agent: Any, required_tags: tuple[str, ...]) -> bool:
    if not required_tags:
        return True
    required = set(required_tags)
    return any(required <= set(getattr(skill, "tags", ())) for skill in agent.skills)


class Team:
    """Team-first coordination root."""

    def __init__(
        self,
        *,
        scope: Scope,
        policy: Policy,
        model_resolver: ModelResolver | None = None,
        default_model_capability: str | None = None,
    ) -> None:
        self.scope = scope
        self.policy = policy
        self._model_resolver = model_resolver
        if default_model_capability is None and model_resolver is not None:
            default_model_capability = next(iter(model_resolver.capabilities), None)
        self._default_model_capability = default_model_capability
        self._agent_specs: dict[str, AgentSpec] = {}
        self._agents: dict[str, Agent] = {}
        self._members: dict[str, Agent] = self._agents
        self._skills: dict[str, Skill] = {}
        self._workflows: dict[str, Any] = {}

    @classmethod
    def local(
        cls,
        *,
        model: Any,
        tenant_id: str = "local",
        namespace: str = "default",
        capability: str = "default",
        profile_name: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        policy: Policy | None = None,
        **defaults: Any,
    ) -> Team:
        """Create a low-ceremony Team with one default model route."""
        route = ModelRoute(
            capability=capability,
            profile=ModelProfile(
                name=profile_name or capability,
                model=model,
                api_base=api_base,
                api_key=api_key,
                defaults=dict(defaults),
            ),
        )
        return cls(
            scope=Scope(tenant_id=tenant_id, namespace=namespace),
            policy=policy if policy is not None else _permissive_policy(),
            model_resolver=ModelResolver([route]),
            default_model_capability=capability,
        )

    def set_model_resolver(self, resolver: ModelResolver) -> ModelResolver:
        self._model_resolver = resolver
        return resolver

    def set_model_routes(self, *routes: ModelRoute) -> ModelResolver:
        resolver = self._model_resolver or ModelResolver()
        for route in routes:
            resolver.register(route)
        self._model_resolver = resolver
        return resolver

    def add_model(
        self,
        capability: str,
        model: Any,
        *,
        profile_name: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        **defaults: Any,
    ) -> ModelRoute:
        """Register a model route without constructing routing internals by hand."""
        route = ModelRoute(
            capability=capability,
            profile=ModelProfile(
                name=profile_name or capability,
                model=model,
                api_base=api_base,
                api_key=api_key,
                defaults=dict(defaults),
            ),
        )
        self.set_model_routes(route)
        return route

    async def add_agent(self, spec: AgentSpec | None = None, /, **kwargs: Any) -> Agent:
        """Register an :class:`AgentSpec`, or build one from keyword sugar."""
        if spec is not None and kwargs:
            raise TypeError("pass either an AgentSpec or keyword fields, not both")
        if spec is None:
            known = {item.name for item in fields(AgentSpec)}
            extras = {key: kwargs.pop(key) for key in list(kwargs) if key not in known}
            if extras:
                kwargs["defaults"] = {**extras, **dict(kwargs.get("defaults", {}))}
            spec = AgentSpec(**kwargs)
        elif not isinstance(spec, AgentSpec):
            raise TypeError("add_agent() requires an AgentSpec or keyword fields")
        return await self._register(spec)

    async def _register(self, spec: AgentSpec) -> Agent:
        if spec.name in self._agent_specs:
            raise ValueError(f"agent {spec.name!r} is already registered")
        if spec.scope is not None and spec.scope.tenant_id != self.scope.tenant_id:
            raise ValueError(
                f"agent scope tenant {spec.scope.tenant_id!r} does not match "
                f"team tenant {self.scope.tenant_id!r}"
            )

        capability = spec.model_capability
        if spec.model is not None:
            capability = capability or f"agent:{spec.name}"
            self.add_model(
                capability,
                spec.model,
                api_base=spec.api_base,
                api_key=spec.api_key,
            )
        else:
            capability = capability or self._default_model_capability
        if capability is None:
            raise TypeError(
                "add_agent() requires model_capability= or a Team default route; "
                "use Team.local(model=...) for the low-ceremony path"
            )
        if self._model_resolver is None:
            raise ValueError("Team has no model_resolver; configure routes before add_agent()")

        route = await self._model_resolver.resolve(
            capability,
            principal=f"agent:{spec.name}",
            scope=self.scope,
            policy=self.policy,
            context={"agent_name": spec.name},
        )
        resolved_scope = replace(spec.scope or self.scope, agent_id=spec.name)
        resolved = replace(
            spec,
            model=route.model,
            model_capability=capability,
            scope=resolved_scope,
            api_base=spec.api_base if spec.api_base is not None else route.api_base,
            api_key=spec.api_key if spec.api_key is not None else route.api_key,
            defaults={**route.defaults, **dict(spec.defaults)},
        )
        self._agent_specs[spec.name] = resolved
        for skill in resolved.skills:
            self._skills.setdefault(skill.id, skill)

        from coactra.agent.facade import build_agent

        agent = await build_agent(resolved, policy=self.policy)
        self._agents[spec.name] = agent
        return agent

    def spec(self, name: str) -> AgentSpec | None:
        """Return the resolved spec registered under ``name``."""
        return self._agent_specs.get(name)

    def add_skill(self, skill: Skill) -> Skill:
        self._skills[skill.id] = skill
        return skill

    def skill(self, skill_id: str) -> Skill | None:
        return self._skills.get(skill_id)

    def assign_skill(self, agent_name: str, skill: Skill) -> Skill:
        agent = self.member(agent_name)
        if agent is None:
            raise KeyError(f"unknown agent {agent_name!r}")
        spec = self._agent_specs[agent_name]
        if not any(existing.id == skill.id for existing in spec.skills):
            self._agent_specs[agent_name] = replace(spec, skills=[*spec.skills, skill])
        agent.add_skill(skill)
        self._skills[skill.id] = skill
        return skill

    def add_workflow(self, workflow: Any) -> Any:
        workflow_name = self._workflow_name(workflow)
        self._workflows[workflow_name] = workflow
        return workflow

    def workflow(self, name: str) -> Any | None:
        return self._workflows.get(name)

    def match_skills(
        self,
        skill_id: str,
        *,
        required_tags: tuple[str, ...] | list[str] = (),
    ) -> list[Agent]:
        tags = tuple(required_tags)
        matches: list[Agent] = []
        for agent in self._agents.values():
            skills = agent.skills
            if any(skill.id == skill_id for skill in skills) and _has_required_tags(
                agent,
                tags,
            ):
                matches.append(agent)
        return matches

    def match_skill(
        self,
        skill_id: str,
        *,
        required_tags: tuple[str, ...] | list[str] = (),
    ) -> Agent | None:
        matches = self.match_skills(skill_id, required_tags=required_tags)
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                f"skill {skill_id!r} is ambiguous for tags {tuple(required_tags)!r}: "
                f"{[agent.name for agent in matches]!r}"
            )
        return matches[0]

    def member(self, name: str) -> Agent | None:
        return self._agents.get(name)

    async def check_workflow_step(
        self,
        *,
        phase: str,
        workflow_name: str,
        step_index: int,
        step: Any,
        agent_name: str,
    ):
        return await self.policy.check(
            PolicyRequest(
                principal=f"workflow:{workflow_name}",
                action=f"workflow.{phase}",
                resource=f"agent:{agent_name}",
                scope=self.scope,
                component="team",
                context={
                    "workflow_name": workflow_name,
                    "step_index": step_index,
                    "instruction": getattr(step, "instruction", ""),
                    "requires_skill": getattr(step, "requires_skill", None),
                    "required_tags": list(getattr(step, "required_tags", ())),
                    "agent": getattr(step, "agent", None),
                    "target_agent": agent_name,
                },
            )
        )

    async def can_talk(self, src: str, dst: str) -> bool:
        src_agent = self.member(src)
        dst_agent = self.member(dst)
        if src_agent is None or dst_agent is None:
            return False
        decision = await self.policy.check(
            PolicyRequest(
                principal=f"agent:{src_agent.name}",
                action="agent.delegate",
                resource=f"agent:{dst_agent.name}",
                scope=self.scope,
                component="team",
                context={
                    "source_agent": src_agent.name,
                    "target_agent": dst_agent.name,
                },
            )
        )
        return decision.outcome is DecisionOutcome.allow

    def roster(self) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for agent in self._agents.values():
            card = getattr(agent, "card", None)
            if isinstance(card, dict):
                cards.append(card)
        return cards

    async def run(self, workflow: str | Any, *args: Any, **kwargs: Any) -> Any:
        resolved = self.workflow(workflow) if isinstance(workflow, str) else workflow
        if resolved is None:
            raise KeyError(f"unknown workflow {workflow!r}")
        return await resolved.run(self, *args, **kwargs)


    @classmethod
    async def from_spec(
        cls,
        *,
        model: Any,
        agents: Sequence[AgentSpec],
        tenant_id: str = "local",
        namespace: str = "default",
        capability: str = "default",
        policy: Policy | None = None,
        scope: Scope | None = None,
        model_resolver: ModelResolver | None = None,
        **defaults: Any,
    ) -> Team:
        if scope is not None or model_resolver is not None:
            team = cls(
                scope=scope or Scope(tenant_id=tenant_id, namespace=namespace),
                policy=policy if policy is not None else _permissive_policy(),
                model_resolver=model_resolver,
                default_model_capability=capability if model_resolver is not None else None,
            )
            if model_resolver is None:
                team.add_model(capability, model, **defaults)
                team._default_model_capability = capability
        else:
            team = cls.local(
                model=model,
                tenant_id=tenant_id,
                namespace=namespace,
                capability=capability,
                policy=policy,
                **defaults,
            )
        for spec in agents:
            await team.add_agent(spec)
        return team

    @staticmethod
    def _workflow_name(workflow: Any) -> str:
        name = getattr(workflow, "name", None)
        if isinstance(name, str) and name:
            return name
        if isinstance(workflow, str) and workflow:
            return workflow
        raise ValueError("workflow must expose a non-empty name")
