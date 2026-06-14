"""Architecture guard: default pytest run must not collect live tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LIVE_TEST_FILES = (
    "tests/agent/test_acceptance_live.py",
    "tests/agent/test_live_zen_agent.py",
    "tests/ai/test_live_zen.py",
    "tests/memory/test_live_integration.py",
)

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_addopts_excludes_live_marker():
    pyproject = PACKAGE_ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert "not live" in text
    assert "live:" in text


def test_live_test_files_define_live_marker():
    for rel in LIVE_TEST_FILES:
        text = (PACKAGE_ROOT / rel).read_text(encoding="utf-8")
        assert "pytest.mark.live" in text, f"{rel} must tag live tests with @pytest.mark.live"


def test_default_collection_excludes_live_tests():
    """Default marker filter must not collect live-marked tests."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-m",
        "not live",
        *LIVE_TEST_FILES,
    ]
    result = subprocess.run(
        cmd,
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # Exit code 5 means no tests collected — live tests were deselected as intended.
    assert result.returncode in {0, 5}, result.stderr
    collected = result.stdout
    assert "deselected" in collected or result.returncode == 5
    assert "test_team_workflow_acceptance" not in collected
    assert "test_live_mem0_remember_recall" not in collected
    assert "test_structured_returns_typed_object_from_qwen" not in collected
    assert "test_agent_create_with_openai_provider_runs_live" not in collected
