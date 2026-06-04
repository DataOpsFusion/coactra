"""Workspace research desk sample.

Shows coactra-workspace as a persistent desk for files, handoff notes, and passive
capability manifests. This sample does not enable local command execution.
"""

from __future__ import annotations

from pprint import pprint

from coactra.workspace import CapabilityManifest, Scope, open_workspace


def prepare_research_desk(topic: str) -> dict[str, object]:
    ws = open_workspace(
        scope=Scope(tenant_id="acme", agent_id="agent-research"),
        ephemeral=True,
    )
    try:
        ws.ensure_layout(
            ["notes", "reports"],
            templates={"notes/TODO.md": "# TODO\n- collect primary sources\n"},
        )
        ws.write("notes/topic.md", f"# Topic\n{topic}\n")
        ws.write("reports/brief.md", f"# Brief\nInitial brief for {topic}.\n")
        ws.handoff(f"Continue research on {topic}; verify claims before publishing.")
        ws.set_manifest(CapabilityManifest(refs=["mcp://browser", "mcp://workspace"]))

        return {
            "ephemeral": True,
            "files": ws.list(),
            "handoff": ws.day_note().strip(),
            "capabilities": ws.manifest().refs,
            "brief": ws.read("reports/brief.md").strip(),
        }
    finally:
        ws.close()


def main() -> None:
    pprint(prepare_research_desk("Q3 support automation opportunities"))


if __name__ == "__main__":
    main()
