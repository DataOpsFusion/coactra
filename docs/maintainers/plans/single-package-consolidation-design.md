# Single-Package Consolidation Design — Superseded

This design document described the collapse of seven Coactra distributions into one
`coactra` package with per-capability optional extras. That consolidation is
complete. The seven separate packages (`coactra-ai`, `coactra-memory`,
`coactra-workspace`, `coactra-jobs`, `coactra-directory`, `coactra-agent`, and the
`coactra` umbrella) are now one `coactra` package with `[memory]`, `[workflow]`,
etc. extras.

The current architecture decisions — three-noun model, build order, and the
rename plan for `jobs` → `workflow` and `directory` → `team` — are in the
authoritative design specs:

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**

**[design/2026-06-06-rename-migration.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-rename-migration.md)**
