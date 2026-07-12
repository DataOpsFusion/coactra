"""Optional workflow recipes built on the core playbook runner."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from coactra.agent.workflow import Workflow
from coactra.workflow.playbook import VerificationReceipt, step

__all__ = [
    "CodeChangeRiskTier",
    "CodeChangeReviewDecision",
    "CodeChangeVerificationBundle",
    "CodeChangeVerificationFinding",
    "CodeChangeWorkflowPlan",
    "VerificationCheck",
    "VerifierRequirement",
    "VerifierRole",
    "code_change",
]


class CodeChangeRiskTier(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class VerifierRequirement(StrEnum):
    required = "required"
    advisory = "advisory"


VerificationKind = Literal["command", "http", "state", "artifact", "manual"]
ReviewOutcome = Literal["approve", "request_changes", "escalate", "uncertain"]


class VerificationCheck(BaseModel):
    """One verification check a specialized verifier should assess."""

    id: str = Field(min_length=1)
    kind: VerificationKind
    instruction: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    success: dict[str, Any] = Field(default_factory=dict)


class VerifierRole(BaseModel):
    """A verification dimension with its own routing and checks."""

    role: str = Field(min_length=1)
    skill: str | None = None
    agent: str | None = None
    required_tags: list[str] = Field(default_factory=list)
    requirement: VerifierRequirement = VerifierRequirement.required
    checks: list[VerificationCheck] = Field(default_factory=list)
    summary: str = ""

    @model_validator(mode="after")
    def _validate_target(self) -> VerifierRole:
        if not self.skill and not self.agent:
            raise ValueError("verifier role requires either skill or agent")
        if self.skill and self.agent:
            raise ValueError("verifier role cannot pin both skill and agent")
        if not self.checks:
            raise ValueError("verifier role requires at least one check")
        return self


class CodeChangeVerificationFinding(BaseModel):
    role: str
    requirement: VerifierRequirement
    passed: bool | None = None
    summary: str = ""
    receipts: list[VerificationReceipt] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    advisory_notes: list[str] = Field(default_factory=list)


class CodeChangeVerificationBundle(BaseModel):
    risk_tier: CodeChangeRiskTier
    findings: list[CodeChangeVerificationFinding] = Field(default_factory=list)
    summary: str = ""


class CodeChangeReviewDecision(BaseModel):
    decision: ReviewOutcome
    summary: str = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    missing_proof: list[str] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)


class CodeChangeWorkflowPlan(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    workflow: Any
    risk_tier: CodeChangeRiskTier
    verifier_roles: list[VerifierRole] = Field(default_factory=list)
    requires_human_approval: bool = False
    verification_bundle_type: type[CodeChangeVerificationBundle] = CodeChangeVerificationBundle
    review_decision_type: type[CodeChangeReviewDecision] = CodeChangeReviewDecision


def _verifier_instruction(role: VerifierRole) -> str:
    lines = [
        f"Act as the {role.role} verifier for this code or operations change.",
        f"Requirement level: {role.requirement.value}.",
    ]
    if role.summary:
        lines.append(role.summary)
    lines.append(
        "Collect evidence for every check you can safely run and "
        "aggregate failures instead of failing fast."
    )
    for check in role.checks:
        lines.append(f"- [{check.kind}] {check.id}: {check.instruction}")
    return "\n".join(lines)


def _review_instruction(
    risk_tier: CodeChangeRiskTier,
    verifier_roles: list[VerifierRole],
) -> str:
    roles = ", ".join(
        f"{role.role}({role.requirement.value})" for role in verifier_roles
    ) or "none"
    return (
        "Review the implementation and the verifier evidence bundle. "
        "Return a structured review decision with one of: approve, "
        "request_changes, escalate, uncertain. "
        f"Risk tier: {risk_tier.value}. Verification coverage: {roles}."
    )


def code_change(
    name: str,
    *,
    implement_instruction: str,
    verifier_roles: list[VerifierRole],
    implement_skill: str | None = None,
    implement_agent: str | None = None,
    implement_tags: tuple[str, ...] | list[str] = (),
    review_skill: str | None = None,
    review_agent: str | None = None,
    review_tags: tuple[str, ...] | list[str] = (),
    reviewer_instruction: str | None = None,
    risk_tier: CodeChangeRiskTier = CodeChangeRiskTier.medium,
    human_approval: Literal["auto", "always", "never"] = "auto",
) -> CodeChangeWorkflowPlan:
    """Build an optional implement -> verify* -> review recipe."""
    if not implement_skill and not implement_agent:
        raise ValueError("code_change requires either implement_skill or implement_agent")
    if implement_skill and implement_agent:
        raise ValueError("code_change implement target cannot pin both skill and agent")
    if not review_skill and not review_agent:
        raise ValueError("code_change requires either review_skill or review_agent")
    if review_skill and review_agent:
        raise ValueError("code_change review target cannot pin both skill and agent")
    if not verifier_roles:
        raise ValueError("code_change requires at least one verifier role")

    steps = [
        step(
            implement_instruction,
            agent=implement_agent,
            requires_skill=implement_skill,
            required_tags=tuple(implement_tags),
        )
    ]
    for role in verifier_roles:
        steps.append(
            step(
                _verifier_instruction(role),
                agent=role.agent,
                requires_skill=role.skill,
                required_tags=tuple(role.required_tags),
            )
        )
    steps.append(
        step(
            reviewer_instruction or _review_instruction(risk_tier, verifier_roles),
            agent=review_agent,
            requires_skill=review_skill,
            required_tags=tuple(review_tags),
        )
    )
    needs_human = human_approval == "always" or (
        human_approval == "auto" and risk_tier is not CodeChangeRiskTier.low
    )
    if needs_human:
        steps.append(
            step(
                "Human approval for reviewed change "
                f"({risk_tier.value} risk). Approve the proof bundle.",
                approve=True,
                approval_only=True,
            )
        )
    return CodeChangeWorkflowPlan(
        workflow=Workflow(name, steps=steps),
        risk_tier=risk_tier,
        verifier_roles=verifier_roles,
        requires_human_approval=needs_human,
    )
