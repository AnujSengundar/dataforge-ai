# DataForge AI Studio

DataForge AI Studio is a SaaS-style data platform that turns raw CSV and Excel files into profiled, warehouse-ready, AI-assisted business intelligence.

## Problem Statement

Freelancers, analysts, founders, and small businesses often work with important data trapped in messy spreadsheets and exports. Before they can make decisions, they need to inspect file quality, infer schemas, clean columns, load data into a database, create analytical models, build dashboards, and explain the results.

DataForge AI Studio is designed to compress that workflow into a structured analytics studio: upload data, profile it, store metadata, load it into PostgreSQL, generate insights, and prepare it for dashboards, AI chat, ML, and executive reporting.

## Key Features

- CSV upload and dataset preview.
- Schema inference and metadata capture.
- Automated data profiling and quality summaries.
- Raw data loading into PostgreSQL staging tables.
- Warehouse-ready modeling path for curated analytics.
- Basic summary insights for uploaded datasets.
- Power BI-ready reporting layer.
- Planned AI chat over dataset metadata and warehouse context.
- Planned Ollama, RAG, MCP, and ML integrations.

## High-Level Architecture

DataForge AI Studio is organized around a modular local-first architecture:

- Frontend for upload, preview, insights, reports, and chat.
- FastAPI backend for orchestration and API boundaries.
- PostgreSQL metadata database for datasets, profiles, schemas, and processing state.
- PostgreSQL warehouse for raw, staging, curated, and analytical tables.
- ETL and profiling services for data processing.
- AI and ML services for advanced analytics workflows.
- MCP server for exposing platform tools to AI agents.
- Power BI layer for dashboards and executive reporting.

See [System Architecture](docs/architecture/system_architecture.md) and [Data Flow](docs/architecture/data_flow.md).

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM and migrations | SQLAlchemy, Alembic |
| Data processing | Pandas |
| Data quality | Great Expectations or Pandera |
| BI | Power BI |
| AI | Ollama, RAG with ChromaDB or Qdrant |
| Agent tooling | MCP |
| Frontend | Next.js or React |
| DevOps | Docker, Docker Compose, GitHub Actions |

See [Tech Stack](docs/architecture/tech_stack.md).

## Current Status

Sprint 1 is focused on Product & Engineering Foundation.

Completed so far:

- Repository initialized.
- PostgreSQL connection verified.
- Environment variables configured.
- Product vision and scope documented.
- System architecture and data flow documented.
- Engineering standards and contribution workflow added.

No production backend implementation has been added yet.

## Roadmap

- Sprint 1: Product & Engineering Foundation.
- Sprint 2: Metadata Engine.
- Sprint 3: Profiling Engine.
- Sprint 4: Warehouse Ingestion.
- Sprint 5: Analytics API.
- Sprint 6: Power BI Layer.
- Sprint 7: ML Layer.
- Sprint 8: AI + Ollama + MCP.
- Sprint 9: Portfolio Website + Deployment.

See [Sprint Plan](docs/engineering/sprint_plan.md).

## Repository Structure

```text
dataforge-ai/
├── backend/                 # Future FastAPI application code
├── docker/                  # Docker and local infrastructure assets
├── docs/
│   ├── architecture/        # System architecture, data flow, ADRs, tech stack
│   ├── engineering/         # Standards, setup, branching, contribution docs
│   └── product/             # Vision, personas, feature scope, MVP requirements
├── etl/                     # Future ingestion and transformation services
├── powerbi/                 # Future Power BI files and semantic model assets
├── tests/                   # Future automated tests
├── warehouse/               # Future SQL models and warehouse scripts
├── .env.example             # Example local environment variables
├── pyproject.toml           # Python project configuration
└── requirements.txt         # Python dependencies
```

## Local Setup

Local setup will be expanded as the backend implementation is introduced.

For now:

1. Install Python 3.11 or 3.12.
2. Install PostgreSQL locally or run it through Docker later.
3. Create a virtual environment.
4. Install dependencies from `requirements.txt`.
5. Copy `.env.example` to `.env` and adjust values for your machine.

See [Environment Setup](docs/engineering/environment_setup.md).

## Contributing

See [Contribution Guide](docs/engineering/contribution_guide.md) and [Coding Standards](docs/engineering/coding_standards.md).

## License

License to be decided. Until a license is added, all rights are reserved by the project owner.
