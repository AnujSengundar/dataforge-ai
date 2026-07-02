# Architecture Decisions

## ADR 001: Use FastAPI for the Backend

**Decision:** Use FastAPI as the primary backend framework.

**Rationale:** FastAPI provides strong typing, automatic OpenAPI documentation, async support, and clean request/response modeling. It fits a data platform where APIs need to coordinate file uploads, metadata operations, profiling services, warehouse loading, and AI endpoints.

**Consequence:** The backend can remain lightweight while still presenting a professional API surface for frontend, AI, MCP, and future integrations.

## ADR 002: Use PostgreSQL First

**Decision:** Use PostgreSQL for both metadata storage and the initial warehouse implementation.

**Rationale:** PostgreSQL is reliable, widely adopted, SQL-native, and strong enough for the MVP. It avoids introducing unnecessary infrastructure before the product workflow is proven.

**Consequence:** The project can demonstrate relational modeling, warehouse staging, curated tables, indexing, migrations, and analytical SQL while remaining easy to run locally.

## ADR 003: Use Local-First Ollama for AI

**Decision:** Use Ollama for local LLM-powered features.

**Rationale:** Ollama supports local-first AI experimentation without requiring paid external AI services. This fits the project goal of a portable portfolio platform and keeps sensitive uploaded data closer to the local environment.

**Consequence:** AI features can be demonstrated through local summarization, metadata chat, and RAG workflows, with the option to add other model providers later if needed.

## ADR 004: Use Power BI for Business Reporting

**Decision:** Use Power BI as the primary dashboard and executive reporting layer.

**Rationale:** Power BI is widely used in business analytics roles and is a strong signal for real-world reporting capability. It pairs well with PostgreSQL-backed curated tables and semantic-model-ready outputs.

**Consequence:** The project can showcase both engineering depth and business-facing communication through dashboards, KPIs, and executive-ready reporting.

## ADR 005: Use Docker Compose for Local Development

**Decision:** Use Docker Compose to run the local platform stack.

**Rationale:** The project includes multiple services, including API, PostgreSQL, AI services, and supporting infrastructure. Docker Compose provides a repeatable local environment without requiring cloud services.

**Consequence:** Reviewers and contributors can run the system consistently, and the project remains demo-friendly.

## ADR 006: Use Metadata-Driven Design

**Decision:** Treat metadata as a first-class product and architecture concept.

**Rationale:** Dataset metadata, profiles, inferred schemas, lineage, processing status, and quality results are central to self-service analytics. They also provide structured grounding for AI chat, report generation, and MCP tools.

**Consequence:** The platform can evolve from simple file upload into a more intelligent analytics studio without redesigning the core workflow.
