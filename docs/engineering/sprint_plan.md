# Sprint Plan

## Sprint 1: Product & Engineering Foundation

Goal: Establish the product direction, architecture, documentation, repository standards, and local development expectations.

Planned outcomes:

- Product vision, personas, feature scope, and MVP requirements.
- System architecture, data flow, tech stack, and ADRs.
- Engineering standards, contribution guide, branching strategy, and setup documentation.
- Professional README, `.gitignore`, and `.env.example`.

## Sprint 2: Metadata Engine

Goal: Build the foundation for tracking uploaded datasets and processing state.

Planned outcomes:

- Dataset metadata model.
- Upload records.
- Schema inference storage.
- Processing status tracking.
- Alembic migrations.

## Sprint 3: Profiling Engine

Goal: Generate repeatable dataset and column-level profiles.

Planned outcomes:

- Numeric, categorical, date, and text profiling.
- Missing-value metrics.
- Uniqueness and distribution summaries.
- Persisted profile results.

## Sprint 4: Warehouse Ingestion

Goal: Load uploaded data into PostgreSQL staging tables.

Planned outcomes:

- Raw file ingestion workflow.
- Staging table creation.
- Row count reconciliation.
- Basic lineage between files, metadata, and staging tables.

## Sprint 5: Analytics API

Goal: Expose dataset metadata, profiles, summaries, and insights through FastAPI endpoints.

Planned outcomes:

- Dataset APIs.
- Profile APIs.
- Summary insight APIs.
- Error handling and response contracts.

## Sprint 6: Power BI Layer

Goal: Prepare data and documentation for dashboarding and executive reporting.

Planned outcomes:

- Curated reporting tables.
- Power BI connection guidance.
- Initial dashboard design.
- KPI and summary reporting definitions.

## Sprint 7: ML Layer

Goal: Add machine learning workflows that create analytical value from uploaded data.

Planned outcomes:

- Forecasting prototype.
- Anomaly detection prototype.
- Model metadata tracking.
- ML result storage.

## Sprint 8: AI + Ollama + MCP

Goal: Add AI-assisted interaction and tool-based access to platform capabilities.

Planned outcomes:

- Ollama-powered dataset summaries.
- RAG over metadata and profile results.
- AI chat over dataset context.
- MCP tools for selected platform operations.

## Sprint 9: Portfolio Website + Deployment

Goal: Package the project as a polished portfolio artifact.

Planned outcomes:

- Portfolio landing page.
- Architecture and demo walkthrough.
- Deployment documentation.
- Screenshots, sample datasets, and demo narrative.
