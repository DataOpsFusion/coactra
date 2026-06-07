"""Research workspace with files, handoff notes, and capabilities.

This sample does not enable local command execution. It shows the workspace as a
scoped file desk that can be passed between agents or processes.
"""

from __future__ import annotations

from pprint import pprint

from coactra.workspace import CapabilityManifest, Scope, open_workspace


def prepare_workspace(topic: str) -> dict[str, object]:
    workspace = open_workspace(
        scope=Scope(tenant_id="acme", agent_id="agent:research"),
        ephemeral=True,
    )
    try:
        workspace.ensure_layout(
            ["notes", "reports"],
            templates={"notes/TODO.md": "# TODO\n- collect primary sources\n"},
        )
        workspace.write("notes/topic.md", f"# Topic\n{topic}\n")
        workspace.write("reports/brief.md", f"# Brief\nInitial brief for {topic}.\n")
        workspace.handoff(f"Continue research on {topic}; verify claims before publishing.")
        workspace.set_manifest(CapabilityManifest(refs=["mcp://browser", "mcp://workspace"]))

        return {
            "files": workspace.list(),
            "handoff": workspace.day_note().strip(),
            "capabilities": workspace.manifest().refs,
            "brief": workspace.read("reports/brief.md").strip(),
        }
    finally:
        workspace.close()


def main() -> None:
    pprint(prepare_workspace("support automation opportunities"))


if __name__ == "__main__":
    main()
