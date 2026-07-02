# Branching Strategy

DataForge AI Studio uses a lightweight Git workflow suitable for a portfolio-grade product with clear sprint-based development.

## `main`

`main` represents the stable project state.

- Keep `main` demo-ready.
- Merge only reviewed and verified work.
- Avoid direct commits except for exceptional maintenance updates.

## `develop`

`develop` is the integration branch for active sprint work.

- Merge completed feature, fix, and documentation branches into `develop`.
- Use this branch to stabilize sprint work before promoting to `main`.
- Keep it working and reasonably clean.

## `feature/*`

Use `feature/*` branches for new product or engineering functionality.

Examples:

- `feature/metadata-engine`
- `feature/profiling-service`
- `feature/analytics-api`

## `fix/*`

Use `fix/*` branches for bug fixes and corrections.

Examples:

- `fix/csv-validation-error`
- `fix/postgres-connection-config`

## `docs/*`

Use `docs/*` branches for documentation-only changes.

Examples:

- `docs/engineering-foundation`
- `docs/architecture-decisions`

## `release/*`

`release/*` branches are optional and can be used when preparing a stable demo milestone.

Examples:

- `release/sprint-1`
- `release/mvp-demo`

## Merge Expectations

- Keep branches focused.
- Rebase or merge from the target branch before opening a PR if needed.
- Ensure tests and documentation are updated before merging.
- Delete branches after merge when they are no longer needed.
