"""Structured workflow verification primitives."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

VerificationStatus = Literal["passed", "failed", "partial", "error"]

_MISSING = object()


class VerificationResult(BaseModel):
    """Result of validating final workflow state against done criteria."""

    status: VerificationStatus
    reason: str = ""
    failures: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "passed"


def read_state_path(state: dict[str, Any], path: str) -> Any:
    """Read dotted paths from workflow state, returning a sentinel if missing."""
    current: Any = state
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def is_missing(value: Any) -> bool:
    return value is _MISSING


def is_error_like(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("ok") is False:
            return True
        if value.get("success") is False:
            return True
        status = str(value.get("status", "")).strip().lower()
        if status in {"error", "failed", "failure", "cancelled"}:
            return True
        return any(key in value for key in ("error", "errors", "exception"))
    if isinstance(value, str):
        lowered = value.strip().lower()
        return lowered.startswith(("error:", "failed:", "failure:"))
    return False


def is_successful_value(value: Any) -> bool:
    if is_missing(value) or value is None:
        return False
    if is_error_like(value):
        return False
    if isinstance(value, dict):
        if value.get("ok") is True or value.get("success") is True:
            return True
        status = str(value.get("status", "")).strip().lower()
        if status in {"ok", "success", "succeeded", "completed", "ready"}:
            return True
    return bool(value)


__all__ = [
    "VerificationResult",
    "VerificationStatus",
    "is_error_like",
    "is_missing",
    "is_successful_value",
    "read_state_path",
]
