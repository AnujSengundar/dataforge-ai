# Environment Setup

## Python Version

Use Python 3.11 or 3.12.

These versions provide strong compatibility with FastAPI, SQLAlchemy, Pandas, testing tools, and modern Python typing features.

## PostgreSQL Requirement

PostgreSQL is required for the metadata database and initial warehouse implementation.

Recommended local defaults:

- Host: `localhost`
- Port: `5432`
- Database: `dataforge`
- User: `postgres`
- Password: `password`

These values are placeholders for local development only.

## Virtual Environment Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

## Dependency Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

If the project later standardizes on `uv`, use the lockfile-based workflow documented at that time.

## Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Required variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy database URL for PostgreSQL. |
| `UPLOAD_DIR` | Local directory for uploaded files. |
| `MAX_UPLOAD_MB` | Maximum upload size in megabytes. |
| `APP_ENV` | Runtime environment name. |

## Basic App Run Placeholder

The backend application entry point will be documented once the FastAPI implementation is introduced.

Expected future command shape:

```bash
uvicorn backend.main:app --reload
```

This command is a placeholder and may change when the backend structure is finalized.

## Database Migrations

Alembic is configured from the project root and reads `DATABASE_URL` from the environment.

Create a migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```bash
alembic upgrade head
```

Check current migration state:

```bash
alembic current
```
