"""Team-first coordination facade.

Team is the alpha assembly and execution root for Coactra applications. It owns
agent, skill, workflow, and model-routing catalogs; routes capability-based work;
and carries canonical scope and policy for its members.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from coactra.agent import Agent
from coactra.agent.skills import Skill, normalize_skills
from coactra.model import ModelProfile, ModelResolver, ModelRoute
from coactra.policy import DecisionOutcome, Policy, PolicyRequest
from coactra.policy import permissive as _permissive_policy
from coactra.scope import Scope
from coactra.team.spec import TeamAgentSpec

__all__ = ["Team", "TeamAgentSpec"]


def _has_required_tags(agent: Any, required_tags: tuple[str, ...]) -> bool:
    if not required_tags:
        return True
    required = set(required_tags)
    for skill in getattr(agent, "_skills", []):
        if required <= set(getattr(skill, "tags", ())):
            return True
    return False


@dataclass(slots=True)
class _AgentSpec:
    name: str
    model: Any | None = None
    model_capability: str | None = None
    instructions: str | None = None
    tools: list[Any] = field(default_factory=list)
    runtime: Any | None = None
    api_base: str | None = None
    api_key: str | None = None
    gateway: str | None = None
    auth: Any = None
    memory: Any = None
    workspace: Any = None
    skills: list[Skill] = field(default_factory=list)
    expose: bool = False
    peers: list[Any] = field(default_factory=list)
    registry: Any | None = None
    learned: Any = None
    procedure_engine: Any | None = None
    procedure_scope: Any | None = None
    allow_unreviewed_learned: bool = False
    tracer: Any | None = None
    defaults: dict[str, Any] = field(default_factory=dict)


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
            routes = getattr(model_resolver, "_routes", {})
            default_model_capability = next(iter(routes), None)
        self._default_model_capability = default_model_capability
        self._agent_specs: dict[str, _AgentSpec] = {}
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
        """Create a low-ceremony local Team for prototypes and examples.

        This is the lazy happy path: one model becomes the default route, policy
        is permissive unless supplied, and ``add_agent("name")`` can omit
        ``model_capability``.
        """
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
        """Register a model route without constructing ModelProfile/ModelRoute by hand."""
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

    async def add_agent(
        self,
        name: str,
        *,
        model: Any | None = None,
        model_capability: str | None = None,
        instructions: str | None = None,
        tools: list[Any] | None = None,
        runtime: Any | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        gateway: str | None = None,
        auth: Any = None,
        memory: Any = None,
        workspace: Any = None,
        skills: Any = None,
        expose: bool = False,
        peers: list[Any] | None = None,
        registry: Any | None = None,
        learned: Any = None,
        procedure_engine: Any | None = None,
        procedure_scope: Any | None = None,
        allow_unreviewed_learned: bool = False,
        tracer: Any | None = None,
        **defaults: Any,
    ) -> Agent:
        """Register and build an Agent owned by this Team."""
        if name in self._agent_specs:
            raise ValueError(f"agent {name!r} is already registered")
        if model is not None:
            effective_model_capability = model_capability or f"agent:{name}"
            self.add_model(
                effective_model_capability,
                model,
                api_base=api_base,
                api_key=api_key,
                **defaults,
            )
        else:
            effective_model_capability = model_capability or self._default_model_capability
        if effective_model_capability is None:
            raise TypeError(
                "add_agent() requires model_capability=, model=, or a Team default route; "
                "use Team.local(model=...) for the low-ceremony path"
            )
        if self._model_resolver is None:
            raise ValueError("Team has no model_resolver; configure routes before add_agent()")

        try:
            route = await self._model_resolver.resolve(
                effective_model_capability,
                principal=f"agent:{name}",
                scope=self.scope,
                policy=self.policy,
                context={"agent_name": name},
            )
        except KeyError as exc:
            raise KeyError(
                f"No model route found for capability {effective_model_capability!r}. "
                "Use Team.local(model=...) for a default local route, "
                "team.add_model('capability', model=...), or add_agent(..., model=...)."
            ) from exc
        resolved_model = route.model
        effective_api_base = api_base if api_base is not None else route.api_base
        effective_api_key = api_key if api_key is not None else route.api_key
        effective_defaults = {**route.defaults, **defaults}

        normalized_skills = normalize_skills(skills)
        spec = _AgentSpec(
            name=name,
            model=resolved_model,
            model_capability=effective_model_capability,
            instructions=instructions,
            tools=list(tools or []),
            runtime=runtime,
            api_base=effective_api_base,
            api_key=effective_api_key,
            gateway=gateway,
            auth=auth,
            memory=memory,
            workspace=workspace,
            skills=normalized_skills,
            expose=expose,
            peers=list(peers or []),
            registry=registry,
            learned=learned,
            procedure_engine=procedure_engine,
            procedure_scope=procedure_scope,
            allow_unreviewed_learned=allow_unreviewed_learned,
            tracer=tracer,
            defaults=effective_defaults,
        )
        self._agent_specs[name] = spec
        for skill in normalized_skills:
            self._skills.setdefault(skill.id, skill)

        from coactra.agent.facade import build_agent

        agent = await build_agent(
            model=resolved_model,
            instructions=instructions,
            tools=list(tools or []),
            runtime=runtime,
            api_base=effective_api_base,
            api_key=effective_api_key,
            gateway=gateway,
            auth=auth,
            name=name,
            tenant=self.scope.tenant_id,
            memory=memory,
            workspace=workspace,
            skills=normalized_skills,
            expose=expose,
            peers=list(peers or []),
            registry=registry,
            learned=learned,
            procedure_engine=procedure_engine,
            procedure_scope=procedure_scope,
            allow_unreviewed_learned=allow_unreviewed_learned,
            tracer=tracer,
            policy=self.policy,
            **effective_defaults,
        )
        self._agents[name] = agent
        return agent

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
            spec.skills.append(skill)
        if not any(existing.id == skill.id for existing in agent._skills):
            agent._skills.append(skill)
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
            skills = getattr(agent, "_skills", [])
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
                f"{[agent._name for agent in matches]!r}"
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
                principal=f"agent:{src_agent._name}",
                action="agent.delegate",
                resource=f"agent:{dst_agent._name}",
                scope=self.scope,
                component="team",
                context={
                    "source_agent": src_agent._name,
                    "target_agent": dst_agent._name,
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
        agents: list[TeamAgentSpec] | tuple[TeamAgentSpec, ...],
        tenant_id: str = "local",
        namespace: str = "default",
        capability: str = "default",
        policy: Policy | None = None,
        scope: Scope | None = None,
        model_resolver: ModelResolver | None = None,
        **defaults: Any,
    ) -> Team:
        """Build a Team from a compact declarative list of agent specs."""
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
            await team.add_agent(
                spec.name,
                model=spec.model,
                model_capability=spec.model_capability,
                instructions=spec.instructions,
                tools=list(spec.tools),
                runtime=spec.runtime,
                api_base=spec.api_base,
                api_key=spec.api_key,
                gateway=spec.gateway,
                auth=spec.auth,
                memory=spec.memory,
                workspace=spec.workspace,
                skills=list(spec.skills),
                expose=spec.expose,
                peers=list(spec.peers),
                registry=spec.registry,
                learned=spec.learned,
                procedure_engine=spec.procedure_engine,
                procedure_scope=spec.procedure_scope,
                allow_unreviewed_learned=spec.allow_unreviewed_learned,
                tracer=spec.tracer,
                **spec.defaults,
            )
        return team

    @staticmethod
    def _workflow_name(workflow: Any) -> str:
        name = getattr(workflow, "name", None)
        if isinstance(name, str) and name:
            return name
        if isinstance(workflow, str) and workflow:
            return workflow
        raise ValueError("workflow must expose a non-empty name")
