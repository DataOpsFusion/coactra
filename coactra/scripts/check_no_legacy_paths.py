"""Fail when docs, tests, or source reintroduce removed alpha import paths."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PATTERNS = (
    "Team([",
    "needs=",
    "coactra.jobs",
    "from coactra.jobs",
    "import coactra.jobs",
    "coactra.directory",
    "from coactra.directory",
    "import coactra.directory",
    "jobs/src/coactra",
    "directory/src/coactra",
    "ledgerflow",
    "[work]",
    "[organization]",
)
SCAN_ROOTS = (
    "coactra/src",
    "coactra/tests",
    "docs",
    "examples",
    "design",
    "README.md",
    "coactra/README.md",
    "CONTRIBUTING.md",
    "coactra/pyproject.toml",
)
ALLOWED = {
    "coactra/scripts/check_no_legacy_paths.py",
    "coactra/tests/arch/test_boundaries.py",
    "docs/maintainers/alpha-release-checklist.md",
    "design/2026-06-09-team-first-alpha-work-orders.md",
}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        path = REPO_ROOT / root
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file())
    return files


def main() -> int:
    hits: list[str] = []
    for path in iter_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWED:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(pattern in line for pattern in PATTERNS):
                hits.append(f"{rel}:{lineno}: {line.strip()}")
    if hits:
        print("Removed alpha paths found:")
        for hit in hits:
            print(hit)
        return 1
    print("No removed alpha import paths found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
