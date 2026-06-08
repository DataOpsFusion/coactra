# Alpha Release Checklist

Run this checklist before cutting an alpha tag. Coactra is still allowed to break APIs, but each release should prove the current surface is intentional.

## Required checks

- `make release-check`
- `make type`
- `python coactra/scripts/check_clean_install.py` builds the wheel and sdist, installs them into fresh virtual environments, and runs public examples from the installed wheel
- `python coactra/scripts/check_no_legacy_paths.py` rejects removed alpha paths in source, tests, docs, examples, and design notes
- `python coactra/scripts/check_live_backends.py` reports configured live checks; set `COACTRA_REQUIRE_LIVE=1` for release-candidate validation
- `git diff --check` has no whitespace errors

`make release-check` intentionally runs the default non-live pytest suite
(`pytest -q -m 'not live'`) plus packaging/docs/release hygiene checks. Keep
Pyright as a separate required gate so type failures do not get hidden inside
the longer packaging validation.

## Surface checks

- architecture contract tests stay green: `tests/arch/test_boundaries.py`, `tests/arch/test_default_suite_no_live.py`, and `scripts/check_clean_install.py`
- top-level `coactra.__all__` contains only the preferred application API
- removed package roots such as `coactra.jobs` and `coactra.directory` remain unimportable
- no docs recommend removed extras such as `[work]` or `[organization]`
- base install imports pure-Python capability roots without optional backend dependencies
- clean wheel install can run the acceptance examples without `PYTHONPATH`

## Human review

- changelog names any breaking import moves
- examples show bring-your-own model, memory/workspace, and MCP toolset usage
- lower-level implementation paths are clearly marked as lower-level, not the preferred application surface
- changelog entry names this alpha's import removals and package moves
