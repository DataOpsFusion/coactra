"""Shared error contract for the dependency-light Coactra shell."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class ErrorCode(StrEnum):
    """Machine-readable error categories for public Coactra boundaries."""

    TIMEOUT = "timeout"
    VALIDATION = "validation"
    PROVIDER = "provider"
    STORAGE = "storage"
    RUNTIME = "runtime"
    PLUGIN = "plugin"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    """Serializable error payload suitable for logs, APIs, and task results."""

    code: ErrorCode
    message: str
    retryable: bool = False
    details: Mapping[str, Any] = MappingProxyType({})


class MissingExtraError(RuntimeError):
    """An optional-extra backend/adapter was used before its extra (and a real
    implementation) exist. Raised with a human-readable install hint message."""


class CoactraError(Exception):
    """Base exception carrying a stable Coactra error code and retry hint."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.INTERNAL,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.info = ErrorInfo(
            code=code,
            message=message,
            retryable=retryable,
            details=MappingProxyType(dict(details or {})),
        )
        self.__cause__ = cause

    @property
    def code(self) -> ErrorCode:
        return self.info.code

    @property
    def retryable(self) -> bool:
        return self.info.retryable

    @property
    def details(self) -> Mapping[str, Any]:
        return self.info.details

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation without the exception cause."""
        return {
            "code": self.code.value,
            "message": self.info.message,
            "retryable": self.retryable,
            "details": dict(self.details),
        }


def coactra_error_from_exception(
    exc: BaseException,
    *,
    code: ErrorCode = ErrorCode.INTERNAL,
    retryable: bool = False,
    details: Mapping[str, Any] | None = None,
) -> CoactraError:
    """Normalize arbitrary exceptions at public boundaries."""
    if isinstance(exc, CoactraError):
        return exc
    return CoactraError(
        str(exc) or exc.__class__.__name__,
        code=code,
        retryable=retryable,
        details=details,
        cause=exc,
    )


__all__ = [
    "CoactraError",
    "ErrorCode",
    "ErrorInfo",
    "MissingExtraError",
    "coactra_error_from_exception",
]
