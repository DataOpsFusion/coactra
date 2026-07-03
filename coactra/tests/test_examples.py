from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_approval_routing_example_runs() -> None:
    package_root = Path(__file__).resolve().parents[1]
    repo_root = package_root.parent
    example = repo_root / "examples" / "projects" / "approval_routing" / "app.py"

    result = subprocess.run(
        [sys.executable, str(example)],
        cwd=repo_root,
        env={**os.environ, "PYTHONPATH": str(package_root / "src")},
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "allowed_reply" in result.stdout
    assert "denied" in result.stdout


def test_root_makefile_declares_quality_targets() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")

    for target in ("test:", "lint:", "type:", "test-examples:"):
        assert target in makefile


def test_acceptance_examples_run() -> None:
    package_root = Path(__file__).resolve().parents[1]
    repo_root = package_root.parent
    examples = [
        repo_root / "examples" / "acceptance" / "bring_existing_model.py",
        repo_root / "examples" / "acceptance" / "bring_existing_memory_workspace.py",
        repo_root / "examples" / "acceptance" / "attach_mcp_toolset.py",
    ]

    for example in examples:
        result = subprocess.run(
            [sys.executable, str(example)],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": str(package_root / "src")},
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == 0, (example, result.stderr)
        assert result.stdout.strip(), example


def test_work_examples_run() -> None:
    package_root = Path(__file__).resolve().parents[1]
    repo_root = package_root.parent
    examples = [
        repo_root / "examples" / "work" / "procedure_runbook.py",
        repo_root / "examples" / "work" / "change_approval_gate.py",
        repo_root / "examples" / "work" / "release_work_lifecycle.py",
    ]

    for example in examples:
        result = subprocess.run(
            [sys.executable, str(example)],
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": str(package_root / "src")},
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == 0, (example, result.stderr)
        assert "status" in result.stdout
