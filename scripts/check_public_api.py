"""Validate the maintained public API inventory.

This is intentionally lightweight: it checks the JSON shape, duplicate roots,
stability tiers, and whether every listed import root appears in docs/API_INDEX.md.
It is not a replacement for generated API diff tooling, but it gives CI a concrete
guardrail before the project has a release-engineering pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
API_JSON = ROOT / "docs" / "public_api.json"
API_INDEX = ROOT / "docs" / "API_INDEX.md"


def main() -> None:
    data = json.loads(API_JSON.read_text())
    tiers = set(data.get("stability_tiers", ()))
    if not tiers:
        raise SystemExit("docs/public_api.json has no stability_tiers")

    roots = data.get("preferred_import_roots", ())
    seen: set[str] = set()
    index_text = API_INDEX.read_text()
    errors: list[str] = []

    for entry in roots:
        root = entry.get("root")
        tier = entry.get("tier")
        purpose = entry.get("purpose")
        if not root or not isinstance(root, str):
            errors.append(f"invalid root entry: {entry!r}")
            continue
        if root in seen:
            errors.append(f"duplicate root: {root}")
        seen.add(root)
        if tier not in tiers:
            errors.append(f"{root}: unknown tier {tier!r}")
        if not purpose:
            errors.append(f"{root}: missing purpose")
        if f"`{root}`" not in index_text:
            errors.append(f"{root}: missing from docs/API_INDEX.md")

    for entry in data.get("compatibility_imports", ()):
        root = entry.get("root")
        preferred = entry.get("preferred")
        if not root or not preferred:
            errors.append(f"invalid compatibility entry: {entry!r}")

    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
