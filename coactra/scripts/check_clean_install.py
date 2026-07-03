"""Build the wheel, install it into a fresh venv, and smoke-test public usage.

This catches editable-install leaks after package moves: hidden PYTHONPATH use, missing
package data, stale import paths, and examples that only work from the source tree.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "coactra"
DIST_DIR = REPO_ROOT / "dist-clean-install"

SMOKE_CODE = """
import importlib.util
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
assert set(coactra.__all__) == expected, coactra.__all__
assert coactra.__version__ != "0.0.0", (
    "refusing hatch VCS fallback version; tag the release or fix the build context"
)
assert importlib.util.find_spec("coactra.jobs") is None
assert importlib.util.find_spec("coactra.directory") is None
for module in [
    "coactra.memory",
    "coactra.workspace",
    "coactra.workflow",
    "coactra.workflow.ledger",
    "coactra.team",
    "coactra.team.directory",
    "coactra.agent",
]:
    __import__(module)
print("clean-install-smoke-ok")
"""

EXAMPLES = [
    "examples/acceptance/bring_existing_model.py",
    "examples/acceptance/bring_existing_memory_workspace.py",
    "examples/acceptance/attach_mcp_toolset.py",
    "examples/work/procedure_runbook.py",
    "examples/work/change_approval_gate.py",
    "examples/work/release_work_lifecycle.py",
]


def run(cmd: list[str], *, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def main() -> int:
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    run(["uv", "build", "--out-dir", str(DIST_DIR)], cwd=PACKAGE_ROOT)
    wheels = sorted(DIST_DIR.glob("*.whl"))
    sdists = sorted(DIST_DIR.glob("*.tar.gz"))
    if len(wheels) != 1:
        raise SystemExit(f"expected exactly one wheel in {DIST_DIR}, found {len(wheels)}")
    if len(sdists) != 1:
        raise SystemExit(f"expected exactly one sdist in {DIST_DIR}, found {len(sdists)}")

    _check_artifact(wheels[0], run_examples=True)
    _check_artifact(sdists[0], run_examples=False)
    return 0


def _check_artifact(artifact: Path, *, run_examples: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="coactra-clean-install-") as tmp:
        venv = Path(tmp) / "venv"
        run([sys.executable, "-m", "venv", str(venv)])
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(python), "-m", "pip", "install", str(artifact)])
        run([str(python), "-c", SMOKE_CODE], env=_clean_env())
        if run_examples:
            run([str(python), "-m", "pip", "install", f"{artifact}[agent,agent-gateway]"])
            for example in EXAMPLES:
                run([str(python), str(REPO_ROOT / example)], env=_clean_env())


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


if __name__ == "__main__":
    raise SystemExit(main())
