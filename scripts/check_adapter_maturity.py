"""Validate the machine-readable adapter maturity manifest.

This keeps ``docs/adapter_maturity.json`` honest against ``docs/ADAPTER_MATURITY.md``
so the two can't silently drift (the JSON had only 5 of ~28 adapters before this
guardrail existed). It checks, for every adapter entry:

- required fields and valid ``maturity`` / ``resume_semantics`` values
- ``resume_semantics`` is present exactly for workflow-runtime adapters
- the referenced ``file`` actually exists on disk (catches moved/renamed code)
- the JSON entry count matches the row count of the ``## Current Matrix`` table
  in ``docs/ADAPTER_MATURITY.md`` (parity guard against one-sided edits)

It is intentionally lightweight and only validates adapter maturity metadata.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "adapter_maturity.json"
MATRIX_MD = ROOT / "docs" / "ADAPTER_MATURITY.md"
WORKFLOW_PACKAGE = "coactra-jobs.workflow"


def _markdown_matrix_row_count(text: str) -> int:
    """Count data rows in the '## Current Matrix' table (header/separator excluded)."""
    rows = 0
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped == "## Current Matrix"
            continue
        if not in_section:
            continue
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        # skip the header row and the |---|---| separator row
        if cells[0].lower() in {"package", ""} and "package" in stripped.lower():
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows += 1
    return rows


def main() -> None:
    data = json.loads(MANIFEST.read_text())
    errors: list[str] = []

    maturity_values = set(data.get("maturity_values", ()))
    resume_values = set(data.get("resume_semantics_values", ()))
    if not maturity_values:
        errors.append("adapter_maturity.json has no maturity_values")
    if not resume_values:
        errors.append("adapter_maturity.json has no resume_semantics_values")

    adapters = data.get("adapters", ())
    if not adapters:
        raise SystemExit("adapter_maturity.json has no adapters")

    seen: set[tuple[str, str]] = set()
    for entry in adapters:
        package = entry.get("package")
        name = entry.get("name")
        label = f"{package}:{name}"

        if not package or not name:
            errors.append(f"adapter entry missing package/name: {entry!r}")
            continue
        key = (package, name)
        if key in seen:
            errors.append(f"duplicate adapter: {label}")
        seen.add(key)

        if entry.get("maturity") not in maturity_values:
            errors.append(f"{label}: invalid maturity {entry.get('maturity')!r}")

        resume = entry.get("resume_semantics")
        if package == WORKFLOW_PACKAGE:
            if resume is None:
                errors.append(f"{label}: workflow-runtime adapter missing resume_semantics")
            elif resume not in resume_values:
                errors.append(f"{label}: invalid resume_semantics {resume!r}")
        elif resume is not None and resume not in resume_values:
            errors.append(f"{label}: invalid resume_semantics {resume!r}")

        rel = entry.get("file")
        if not rel:
            errors.append(f"{label}: missing file path")
        elif not (ROOT / rel).exists():
            errors.append(f"{label}: file does not exist: {rel}")

    md_rows = _markdown_matrix_row_count(MATRIX_MD.read_text())
    if md_rows != len(adapters):
        errors.append(
            f"adapter count mismatch: docs/ADAPTER_MATURITY.md has {md_rows} rows, "
            f"docs/adapter_maturity.json has {len(adapters)} entries"
        )

    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
