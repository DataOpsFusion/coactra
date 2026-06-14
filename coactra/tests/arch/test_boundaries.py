"""Architecture guard tests for public boundaries and deleted legacy."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def test_top_level_exports_resolve_without_eager_runtime_imports():
    import coactra

    for name in coactra.__all__:
        assert getattr(coactra, name) is not None


def test_agent_runtime_port_is_owned_by_ports_module():
    import coactra.agent as agent
    from coactra.agent.ports import AgentRuntimePort

    assert agent.AgentRuntimePort is AgentRuntimePort


def test_workflow_surface_does_not_export_agent_concepts():
    import coactra.workflow as workflow

    for name in ["Agent", "Run", "AgentRef", "RemotePeer", "Team"]:
        assert not hasattr(workflow, name), name


def test_playbook_module_stays_dependency_light():
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "coactra" / "workflow" / "playbook.py").read_text()
    for forbidden in ["pydantic_ai", "langgraph", "temporalio", "prefect"]:
        assert forbidden not in source
    assert "import yaml" in source
    assert "def from_yaml" in source


def test_removed_legacy_modules_stay_deleted():
    removed = [
        "coactra.agent.team",
        "coactra.jobs",
        "coactra.directory",
        "coactra.team.directory.store",
        "coactra.directory.store",
        "coactra.directory.sqlite_store",
        "coactra.team.directory.sqlite_store",
        "coactra.workspace.integrations.organization",
    ]
    for module_name in removed:
        sys.modules.pop(module_name, None)
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)


def test_removed_work_extra_stays_removed():
    import tomllib

    extras = tomllib.loads(Path("pyproject.toml").read_text())["project"]["optional-dependencies"]
    assert "workflow" in extras
    assert "team" in extras
    assert "work" not in extras
    assert "organization" not in extras


def test_top_level_public_api_stays_small():
    import coactra

    expected = {
        "Agent",
        "CoactraError",
        "Decision",
        "DecisionOutcome",
        "ErrorCode",
        "MissingExtraError",
        "ModelProfile",
        "ModelResolver",
        "ModelRoute",
        "Policy",
        "PolicyRequest",
        "RemotePeer",
        "Run",
        "Scope",
        "Skill",
        "StaticToken",
        "Team",
        "ValidationError",
        "Workflow",
        "__version__",
    }
    assert set(coactra.__all__) == expected


def test_api_index_documents_the_exact_top_level_contract():
    import coactra

    api_index = Path(__file__).resolve().parents[3] / "docs" / "API_INDEX.md"
    text = api_index.read_text()
    for name in coactra.__all__:
        assert name in text
    assert "Removed alpha roots" in text
