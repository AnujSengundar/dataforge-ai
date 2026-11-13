# Turning Point

An AI investigation studio for fans: test a claim about a real match, race, or adaptation, then challenge the verdict with evidence.

| Case | Question | Evidence |
| --- | --- | --- |
| 2016 T20 World Cup final | Did England lose it in the final over? | All 124 chase deliveries, required run rate, wickets, and scoring windows |
| 2021 Monaco Grand Prix | Did Vettel's later stop gain him position? | Pit-lane transit, rejoin order, and classification |
| Fullmetal Alchemist vs Brotherhood | Does the anime prime viewers to question Cornello earlier? | Side-by-side scene annotations with an opt-in reveal |

## Run Locally

Install Git, Python 3.12, and PostgreSQL. During PostgreSQL setup, note the password for the
`postgres` user and leave the default port at `5432` unless it is already in use. You don't need
Node.js, Docker, an API key, or Ollama to try the bundled cases.

### 1. Open the project

If the Turning Point branch has been published to GitHub, clone it from a terminal:

```sh
git clone --branch codex/turning-point https://github.com/AnujSengundar/dataforge-ai.git
cd dataforge-ai
```

Already have the repository? Open a terminal in its root and run `git switch codex/turning-point`.
Run the remaining commands from this folder, where you'll see `alembic.ini` and `requirements.txt`.

### 2. Install the Python dependencies

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**macOS or Linux**

```sh
python3.12 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

The commands call the virtual environment's Python directly, so you don't need to activate it.
If you already have an `.env` file, skip the copy and add the Turning Point setting below to it.

### 3. Create and configure the database

Make sure PostgreSQL is running. Connect with `psql -h localhost -p 5432 -U postgres -d postgres`
and enter the password you chose during installation. If `psql` isn't on your PATH, open pgAdmin,
connect to your local server, and open **Query Tool** on the default `postgres` database instead.
Run this SQL once:

```sql
CREATE DATABASE turning_point;
```

If the database already exists, skip the SQL. Exit `psql` with `\q` before returning to the app
commands. Open `.env` in your editor and set:

```dotenv
TURNING_POINT_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/turning_point
```

Replace `YOUR_PASSWORD` with your PostgreSQL password. If it contains URL-reserved characters,
encode them (for example, `@` becomes `%40`). Adjust the user or port if your setup differs.
Do not point this setting at the old DataForge database.

### 4. Create the tables and start the app

**Windows PowerShell**

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.turning_point.main:app --port 8765
```

**macOS or Linux**

```sh
./.venv/bin/python -m alembic upgrade head
./.venv/bin/python -m uvicorn backend.turning_point.main:app --port 8765
```

Only start Uvicorn once the migration succeeds. Keep the terminal open and visit
[http://127.0.0.1:8765](http://127.0.0.1:8765). You should see the cricket case and its timeline.
Press **Ctrl+C** to stop the server. The [API reference](http://127.0.0.1:8765/docs) is also available.

| Problem | What to check |
| --- | --- |
| PostgreSQL connection refused | Start PostgreSQL and check the host and port in `.env`. |
| Password authentication failed | Check the database username and password, including URL encoding. |
| Database does not exist | Run the SQL in step 3 and confirm the database name in `.env`. |
| Port 8765 is already in use | Use `--port 8766` and open `http://127.0.0.1:8766` instead. |

## Three-Minute Walkthrough

1. Open **Cricket** and investigate the suggested claim.
2. Open the citation for the required rate entering the last over. West Indies needed 19 from six legal balls.
3. Select **Make the opposing case**. Compare the verdicts and inspect the earlier scoring window.
4. Switch to **Formula 1** to compare pit-lane times, or **Adaptations** to compare openings without enabling the reveal.

## Enable Local AI (Optional)

Install and open Ollama. If it isn't already running, start it with `ollama serve` in a separate
terminal. In another terminal, download the model:

```sh
ollama pull qwen2.5:1.5b
```

Run an investigation again. The result shows the model name when Ollama returns a valid verdict.
Otherwise it shows **evidence-only**: suggested claims still have curated verdicts, while custom
claims are marked insufficient. To use a different model or endpoint, set `TURNING_POINT_MODEL`
or `TURNING_POINT_OLLAMA` in `.env` and restart Turning Point.

## Design

FastAPI serves the case library, investigation API, and browser UI. Python computes sports facts
from pinned evidence; Ollama chooses bounded tools and classifies claims against their results.
The model can return fact IDs, not new evidence text. The server checks citations against the
current case and spoiler level. PostgreSQL stores the original and reviewed results separately,
including source version, model, tool names, and elapsed time.

The release is local-first: three curated cases, no live feeds, simulations, open uploads, or public
multi-user deployment. Turning Point is the only application on this branch. The previous
DataForge implementation and migration history remain on the original sprint branches.

See [evidence sources and evaluation](docs/turning_point.md). The application code has no
declared license; third-party data and referenced works have separate terms.
