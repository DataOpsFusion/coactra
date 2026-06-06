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
    SECURITY = "security"
    PERMISSION = "permission"


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    """Serializable error payload suitable for logs, APIs, and task results."""

    code: ErrorCode
    message: str
    retryable: bool = False
    details: Mapping[str, Any] = MappingProxyType({})


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


class ConfigError(CoactraError):
    """Misconfiguration or missing optional install extra."""


class ValidationError(CoactraError):
    """Input or contract validation failed."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.VALIDATION,
            retryable=retryable,
            details=details,
            cause=cause,
        )


class MissingExtraError(ConfigError):
    """An optional-extra backend/adapter was used before its extra (and a real
    implementation) exist. Raised with a human-readable install hint message."""

    def __init__(self, message: str, *, extra: str | None = None) -> None:
        if extra is None and "requires" not in message and "install" not in message:
            extra = message
            message = (
                f"this backend requires the optional '{extra}' extra; "
                f"install with: pip install coactra[{extra}]"
            )
        super().__init__(message, code=ErrorCode.PLUGIN)
        self.extra = extra


class AdapterError(CoactraError):
    """An integration adapter failed at a public boundary."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PROVIDER,
            retryable=retryable,
            details=details,
            cause=cause,
        )


class ExecutionError(CoactraError):
    """Runtime execution failed after validation and setup."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.RUNTIME,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            retryable=retryable,
            details=details,
            cause=cause,
        )


class TimeoutError(ExecutionError):
    """Execution exceeded its deadline."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = True,
        details: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.TIMEOUT,
            retryable=retryable,
            details=details,
            cause=cause,
        )


class PermissionDeniedError(CoactraError):
    """Authorization denied for the requested action."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PERMISSION,
            retryable=retryable,
            details=details,
            cause=cause,
        )


class SecurityError(CoactraError):
    """Security boundary violation or unsafe configuration."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.SECURITY,
            retryable=retryable,
            details=details,
            cause=cause,
        )


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
    "AdapterError",
    "CoactraError",
    "ConfigError",
    "ErrorCode",
    "ErrorInfo",
    "ExecutionError",
    "MissingExtraError",
    "PermissionDeniedError",
    "SecurityError",
    "TimeoutError",
    "ValidationError",
    "coactra_error_from_exception",
]
