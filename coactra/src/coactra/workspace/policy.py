"""CliPolicy — a desk-LOCAL command allow/deny gate.

This is the charter's "CLI policy": which commands the agent may run inside its own desk.
It is NOT organization policy — no roles, no escalation, no reporting (organization owns
that).

DESIGN OVERRIDE (locked): commands are an arg-list (argv: list[str]), never a shell
string — there is no shell=True anywhere. The gate therefore operates on argv, not on a
joined command string. Patterns are token sequences (split on whitespace); a pattern
matches argv when it is a leading-token prefix of argv (e.g. deny "git push" matches
["git", "push", "origin", "main"]). deny wins over allow; a non-empty allowlist is
default-deny.
"""

from __future__ import annotations

import shlex
from collections.abc import Sequence

from pydantic import BaseModel, Field

from coactra.workspace.errors import WorkspaceError


class PolicyError(WorkspaceError):
    """Raised when a command is blocked by the desk CLI policy."""


def to_argv(command: str | Sequence[str]) -> list[str]:
    """Normalize a str-or-arg-list command into an argv list (shell=False, no shell parse)."""
    if isinstance(command, str):
        return shlex.split(command)
    return list(command)


class CliPolicy(BaseModel):
    """Allow/deny gate evaluated (on argv) before a command reaches the backend."""

    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)

    @classmethod
    def safe_default(cls) -> CliPolicy:
        """Conservative policy used when local subprocess execution is enabled implicitly.

        This helper gives local development an explicit conservative allowlist.
        """
        return cls(
            allow=["pwd", "ls", "cat", "echo"],
            deny=["rm", "git push", "curl", "wget", "ssh", "scp", "python", "python3"],
        )

    def check(self, command: str | Sequence[str]) -> list[str]:
        """Validate command; return the normalized argv. Raises PolicyError if blocked."""
        argv = to_argv(command)
        if not argv:
            raise PolicyError("empty command is not allowed")
        for pattern in self.deny:
            if self._matches(argv, pattern):
                raise PolicyError(f"command blocked by deny rule: {pattern!r}")
        if not self.allow:
            raise PolicyError("CliPolicy requires an explicit allowlist")
        if not any(self._matches(argv, p) for p in self.allow):
            raise PolicyError(f"command not in allowlist: {argv!r}")
        return argv

    @staticmethod
    def _matches(argv: list[str], pattern: str) -> bool:
        tokens = pattern.split()
        if not tokens:
            return False
        return argv[: len(tokens)] == tokens
