# Coding Standards

## Python Style

- Use clear, idiomatic Python with small functions and explicit boundaries.
- Prefer readability over clever abstractions.
- Keep modules focused on one responsibility.
- Format consistently with the project formatter once configured.
- Avoid implementation shortcuts that hide data quality or processing errors.

## Type Hints

- Use type hints for public functions, service methods, API handlers, and data models.
- Prefer explicit return types.
- Use typed configuration and request/response models where practical.
- Avoid `Any` unless the data shape is genuinely unknown.

## Service-Layer Pattern

- Keep API routes thin.
- Place business logic in service modules.
- Keep persistence logic separate from route handlers.
- Use clear service boundaries for metadata, profiling, ingestion, AI, ML, and reporting.
- Prefer dependency injection for database sessions and configurable services.

## SQLAlchemy Usage

- Use SQLAlchemy for database models and database access.
- Keep ORM models aligned with Alembic migrations.
- Avoid raw SQL in application code unless it is justified for analytics, performance, or warehouse-specific behavior.
- Keep transaction boundaries explicit.
- Do not mix metadata database concerns with warehouse table concerns without a clear interface.

## FastAPI Conventions

- Use Pydantic models for request and response contracts.
- Keep route names and prefixes resource-oriented.
- Return consistent response shapes.
- Validate inputs at the API boundary.
- Use dependency functions for shared resources such as settings and database sessions.
- Keep long-running file processing out of route handlers as the system matures.

## Error Handling

- Raise domain-specific errors inside services.
- Convert service errors into clear API responses at the boundary.
- Avoid leaking internal stack traces to users.
- Include enough context in logs to debug failures.
- Treat invalid files, unsupported formats, failed validations, and database errors as expected failure modes.

## Logging

- Use structured, meaningful log messages.
- Log workflow milestones such as upload received, validation completed, profile generated, and staging load completed.
- Do not log secrets, full connection strings, or sensitive uploaded data.
- Prefer request IDs or job IDs for tracing multi-step workflows.

## Testing Expectations

- Add unit tests for service logic.
- Add integration tests for database workflows.
- Add API tests for FastAPI routes when endpoints are introduced.
- Test failure paths, not only successful flows.
- Use small representative fixtures for file-processing tests.

## Naming Conventions

- Use `snake_case` for Python variables, functions, modules, database columns, and table names.
- Use `PascalCase` for classes and Pydantic models.
- Use descriptive names for services, repositories, and schemas.
- Prefer domain names such as `dataset`, `profile`, `upload`, `schema_inference`, and `staging_table`.
- Keep branch, migration, and test names tied to the feature being changed.
