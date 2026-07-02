# Contribution Guide

## Local Setup

1. Clone the repository.
2. Install Python 3.11 or 3.12.
3. Create and activate a virtual environment.
4. Install dependencies from `requirements.txt`.
5. Copy `.env.example` to `.env`.
6. Update local environment values as needed.
7. Start PostgreSQL locally or through Docker once Docker Compose is introduced.
8. Run tests before opening a pull request once test suites are available.

See [Environment Setup](environment_setup.md) for details.

## Branch Naming

Use short, descriptive branch names:

- `feature/<short-description>` for new functionality.
- `fix/<short-description>` for bug fixes.
- `docs/<short-description>` for documentation changes.
- `release/<version-or-date>` for release preparation when needed.

Examples:

- `feature/metadata-engine`
- `fix/upload-validation`
- `docs/sprint-1-foundation`

## Commit Message Style

Use concise, action-oriented commit messages.

Recommended format:

```text
type: short summary
```

Examples:

- `docs: add engineering foundation`
- `feature: add metadata models`
- `fix: handle invalid csv uploads`
- `test: cover schema inference service`

## Pull Request Checklist

- The change has a clear purpose and scope.
- Documentation is updated when behavior, setup, architecture, or workflow changes.
- Tests are added or updated when implementation code changes.
- Existing tests pass locally.
- Environment variables are documented in `.env.example`.
- No secrets, local files, uploaded datasets, or generated artifacts are committed.
- The PR description explains the user or engineering impact.

## Documentation Expectations

- Keep docs concise, professional, and current.
- Link related product, architecture, and engineering documents where helpful.
- Update ADRs when a meaningful technical decision changes.
- Document setup changes before expecting others to run them.

## Testing Expectations

- Implementation changes should include appropriate tests.
- Prefer focused tests that verify behavior rather than internal details.
- Include failure-path tests for file parsing, validation, database writes, and API errors.
- Do not rely on large local datasets in tests.
