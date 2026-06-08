"""Review and version induced procedures before they become active."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from coactra.workflow.domain.models import Procedure
from coactra.workflow.domain.scope import Scope
from coactra.workflow.induction import ReasoningTrace, induce


def utc_now() -> datetime:
    return datetime.now(UTC)


class CandidateStatus(StrEnum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    promoted = "promoted"


class ProcedureCandidate(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    scope: Scope
    procedure: Procedure
    proposed_by: str = Field(min_length=1)
    status: CandidateStatus = CandidateStatus.proposed
    reviewed_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    reviewed_at: datetime | None = None


class ProcedureVersion(BaseModel):
    procedure: Procedure
    version: int = Field(ge=1)
    promoted_by: str = Field(min_length=1)
    candidate_id: str | None = None
    rollback_of: int | None = None
    promoted_at: datetime = Field(default_factory=utc_now)


class InMemoryProcedurePromotionStore:
    """Tenant-scoped reference catalog with explicit review, promotion, and rollback."""

    def __init__(self) -> None:
        self._candidates: dict[str, dict[str, ProcedureCandidate]] = {}
        self._versions: dict[str, dict[str, list[ProcedureVersion]]] = {}

    def propose(
        self,
        trace: ReasoningTrace,
        scope: Scope,
        *,
        proposed_by: str,
    ) -> ProcedureCandidate:
        candidate = ProcedureCandidate(
            scope=scope,
            procedure=induce(trace),
            proposed_by=proposed_by,
        )
        self._candidate_bucket(scope)[candidate.id] = candidate.model_copy(deep=True)
        return candidate

    def approve(self, candidate_id: str, scope: Scope, *, reviewed_by: str) -> ProcedureCandidate:
        candidate = self._candidate(candidate_id, scope)
        if candidate.status is not CandidateStatus.proposed:
            raise ValueError("only proposed procedures can be approved")
        candidate.status = CandidateStatus.approved
        candidate.reviewed_by = reviewed_by
        candidate.reviewed_at = utc_now()
        return self._save_candidate(candidate)

    def reject(self, candidate_id: str, scope: Scope, *, reviewed_by: str) -> ProcedureCandidate:
        candidate = self._candidate(candidate_id, scope)
        if candidate.status is not CandidateStatus.proposed:
            raise ValueError("only proposed procedures can be rejected")
        candidate.status = CandidateStatus.rejected
        candidate.reviewed_by = reviewed_by
        candidate.reviewed_at = utc_now()
        return self._save_candidate(candidate)

    def promote(self, candidate_id: str, scope: Scope, *, promoted_by: str) -> ProcedureVersion:
        candidate = self._candidate(candidate_id, scope)
        if candidate.status is not CandidateStatus.approved:
            raise ValueError("procedure must be approved before promotion")
        version = self._append_version(
            candidate.procedure,
            scope,
            promoted_by=promoted_by,
            candidate_id=candidate.id,
        )
        candidate.status = CandidateStatus.promoted
        self._save_candidate(candidate)
        return version

    def rollback(
        self, name: str, version: int, scope: Scope, *, promoted_by: str
    ) -> ProcedureVersion:
        target = self.version(name, version, scope)
        return self._append_version(
            target.procedure,
            scope,
            promoted_by=promoted_by,
            rollback_of=version,
        )

    def active(self, name: str, scope: Scope) -> ProcedureVersion | None:
        versions = self.versions(name, scope)
        return versions[-1] if versions else None

    def version(self, name: str, version: int, scope: Scope) -> ProcedureVersion:
        for item in self.versions(name, scope):
            if item.version == version:
                return item
        raise KeyError((name, version))

    def versions(self, name: str, scope: Scope) -> list[ProcedureVersion]:
        return [item.model_copy(deep=True) for item in self._version_bucket(scope).get(name, [])]

    def _candidate(self, candidate_id: str, scope: Scope) -> ProcedureCandidate:
        candidate = self._candidate_bucket(scope).get(candidate_id)
        if candidate is None:
            raise KeyError(candidate_id)
        return candidate.model_copy(deep=True)

    def _save_candidate(self, candidate: ProcedureCandidate) -> ProcedureCandidate:
        self._candidate_bucket(candidate.scope)[candidate.id] = candidate.model_copy(deep=True)
        return candidate

    def _append_version(
        self,
        procedure: Procedure,
        scope: Scope,
        *,
        promoted_by: str,
        candidate_id: str | None = None,
        rollback_of: int | None = None,
    ) -> ProcedureVersion:
        versions = self._version_bucket(scope).setdefault(procedure.name, [])
        version = ProcedureVersion(
            procedure=procedure.model_copy(deep=True),
            version=len(versions) + 1,
            promoted_by=promoted_by,
            candidate_id=candidate_id,
            rollback_of=rollback_of,
        )
        versions.append(version.model_copy(deep=True))
        return version

    def _candidate_bucket(self, scope: Scope) -> dict[str, ProcedureCandidate]:
        return self._candidates.setdefault(scope.key, {})

    def _version_bucket(self, scope: Scope) -> dict[str, list[ProcedureVersion]]:
        return self._versions.setdefault(scope.key, {})
