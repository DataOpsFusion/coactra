"""Run environment-gated live backend checks for release candidates.

Default mode is informational: configured live checks run, missing credentials are
reported as skipped. Set COACTRA_REQUIRE_LIVE=1 for release-candidate validation,
where every listed live surface must be configured and pass.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REQUIRE_LIVE = os.getenv("COACTRA_REQUIRE_LIVE") == "1"
RUN_LIVE = os.getenv("COACTRA_RUN_LIVE") == "1" or REQUIRE_LIVE
TIMEOUT_SECONDS = int(os.getenv("COACTRA_LIVE_TIMEOUT_SECONDS", "180"))


@dataclass(frozen=True)
class LiveCheck:
    name: str
    tests: tuple[str, ...]
    env_any: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()

    def ready(self) -> tuple[bool, str]:
        missing_env = [key for key in self.env_any if not _env_or_known_file(key)]
        missing_modules = [module for module in self.modules if importlib.util.find_spec(module) is None]
        if missing_env:
            return False, "missing env " + ", ".join(missing_env)
        if missing_modules:
            return False, "missing modules " + ", ".join(missing_modules)
        return True, "configured"


def _env_or_known_file(key: str) -> str | None:
    if os.getenv(key):
        return os.getenv(key)
    if key == "OC_KEY" and Path("/tmp/oc.key").exists():
        return Path("/tmp/oc.key").read_text().strip()
    return None


CHECKS = [
    LiveCheck(
        name="opencode-zen-agent",
        tests=(
            "tests/ai/test_live_zen.py",
            "tests/agent/test_live_zen_agent.py",
            "tests/agent/test_acceptance_live.py",
        ),
        env_any=("OC_KEY",),
    ),
    LiveCheck(
        name="mem0",
        tests=("tests/memory/test_live_integration.py::test_live_mem0_remember_recall",),
        env_any=("OPENAI_API_KEY",),
        modules=("mem0",),
    ),
    LiveCheck(
        name="graphiti",
        tests=("tests/memory/test_live_integration.py::test_live_graphiti_remember_recall",),
        env_any=("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"),
        modules=("graphiti_core",),
    ),
]


def main() -> int:
    failures: list[str] = []
    skipped: list[str] = []
    for check in CHECKS:
        ready, reason = check.ready()
        if not ready:
            skipped.append(f"{check.name}: {reason}")
            continue
        if not RUN_LIVE:
            print(f"Configured live check not executed without COACTRA_RUN_LIVE=1: {check.name}")
            continue
        cmd = [sys.executable, "-m", "pytest", "-q", *check.tests]
        print("+", " ".join(cmd), flush=True)
        try:
            result = subprocess.run(cmd, cwd=PACKAGE_ROOT, check=False, timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            print(f"Live check timed out after {TIMEOUT_SECONDS}s: {check.name}")
            failures.append(check.name)
            continue
        if result.returncode:
            failures.append(check.name)

    if skipped:
        print("Skipped live checks:")
        for item in skipped:
            print(f"- {item}")
    if failures:
        print("Failed live checks:")
        for item in failures:
            print(f"- {item}")
        return 1
    if skipped and REQUIRE_LIVE:
        print("COACTRA_REQUIRE_LIVE=1 but some live checks were not configured.")
        return 1
    if not skipped and RUN_LIVE:
        print("All configured live checks passed.")
    elif not RUN_LIVE:
        print("Live checks were inventoried only. Set COACTRA_RUN_LIVE=1 to execute configured checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
