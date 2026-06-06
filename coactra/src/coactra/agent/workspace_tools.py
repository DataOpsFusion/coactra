"""workspace_tools — expose a Workspace as a list of agent tool callables.

Each returned callable is a plain Python function with type hints and a docstring so that
pydantic-ai (or any compatible framework) can extract the tool schema from it.

Security note (OWASP: command execution gating):
  - ``run`` is ONLY included in the returned list when ``allow_run=True``.
  - The ``allow`` parameter is an explicit allowlist of program names (argv[0]).  An empty
    allowlist is default-deny — no commands are permitted.  This means
    ``workspace_tools(ws, allow_run=True, allow=())`` returns a ``run`` function that
    refuses every invocation; callers must enumerate the exact programs they trust.
  - The gate operates on the program token (argv[0]) extracted from the command string via
    ``shlex.split``, before ``workspace.run`` is ever called.
"""

from __future__ import annotations

import shlex
from collections.abc import Callable

from coactra.workspace.desk import Workspace
from coactra.workspace.policy import PolicyError


def workspace_tools(
    workspace: Workspace,
    *,
    allow_run: bool = False,
    allow: tuple[str, ...] = (),
) -> list[Callable]:
    """Return agent-tool callables backed by *workspace*.

    Parameters
    ----------
    workspace:
        The ``Workspace`` instance the tools will operate on.
    allow_run:
        When ``False`` (default) the returned list does NOT contain ``run`` at all.
        When ``True``, a ``run`` tool is included but each invocation is gated by the
        ``allow`` allowlist.
    allow:
        Tuple of permitted program names (argv[0]).  Evaluated only when
        ``allow_run=True``.  An empty tuple means *no* commands are permitted
        (default-deny).

    Returns
    -------
    list[Callable]
        Plain Python functions — one per enabled capability — each with type hints and a
        docstring that doubles as the tool schema description.
    """

    def read_file(path: str) -> str:
        """Read a file from the workspace and return its text content.

        Parameters
        ----------
        path:
            Relative path inside the workspace root.

        Returns
        -------
        str
            The full text content of the file.
        """
        return workspace.read(path)

    def write_file(path: str, content: str) -> str:
        """Write text content to a file in the workspace.

        Creates the file (and any missing parent directories) if it does not exist;
        overwrites it if it does.

        Parameters
        ----------
        path:
            Relative path inside the workspace root.
        content:
            The text to write to the file.

        Returns
        -------
        str
            A confirmation message indicating the file was written successfully.
        """
        workspace.write(path, content)
        return f"wrote {len(content)} characters to {path}"

    def list_files() -> list[str]:
        """List all files currently present in the workspace.

        Returns
        -------
        list[str]
            Sorted list of relative file paths inside the workspace root.
        """
        return workspace.list()

    tools: list[Callable] = [read_file, write_file, list_files]

    if allow_run:
        # Capture allow in closure for the gating check.
        _allow: frozenset[str] = frozenset(allow)

        def run(command: str) -> str:
            """Run a shell command inside the workspace and return its output.

            The command is gated: only programs whose name (argv[0]) appears in the
            configured allowlist may execute.  Commands outside the allowlist raise
            ``PolicyError`` before any subprocess is started.

            Parameters
            ----------
            command:
                Command string (parsed with ``shlex.split``; shell=False).

            Returns
            -------
            str
                Combined stdout of the completed command, with stderr appended on
                non-zero exit.
            """
            try:
                argv = shlex.split(command)
            except ValueError as exc:
                raise PolicyError(f"could not parse command: {exc}") from exc

            if not argv:
                raise PolicyError("empty command is not allowed")

            program = argv[0]
            if program not in _allow:
                raise PolicyError(
                    f"command {program!r} is not in the tool allowlist; "
                    f"permitted programs: {sorted(_allow)}"
                )

            result = workspace.run(command)
            if result.ok:
                return result.stdout
            return result.stdout + (f"\n[stderr]: {result.stderr}" if result.stderr else "")

        tools.append(run)

    return tools
