# GitHub Actions

- **CI** ([ci.yml](ci.yml)) — lint, non-live tests, docs, typecheck, clean install, live inventory.
- **Docs** ([docs.yml](docs.yml)) — strict MkDocs build on doc changes.
- **Release** ([release.yml](release.yml)) — tag-triggered PyPI publish via Trusted Publishing.

Manual smoke builds use `uv build` locally or the `build` job in CI. The default
test job excludes `live` tests; live checks are inventoried unless explicitly run
with `COACTRA_RUN_LIVE=1`. The deprecated `workflow.yml` publish workflow was
removed to avoid duplicate release paths.
