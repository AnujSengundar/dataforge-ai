# Turning Point

An AI investigation studio for fans: test a claim about a real match, race, or adaptation, then challenge the verdict with evidence.

| Case | Question | Evidence |
| --- | --- | --- |
| 2016 T20 World Cup final | Did England lose it in the final over? | All 124 chase deliveries, required run rate, wickets, and scoring windows |
| 2021 Monaco Grand Prix | Did Vettel's later stop gain him position? | Pit-lane transit, rejoin order, and classification |
| Fullmetal Alchemist vs Brotherhood | Does the anime prime viewers to question Cornello earlier? | Side-by-side scene annotations with an opt-in reveal |

## Run Locally

Requires Python 3.12 and a local PostgreSQL database. Set `DATABASE_URL` in `.env` using [the example](.env.example). Run from the repository root with the virtual environment activated:

```sh
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn backend.turning_point.main:app --port 8765
```

Open [Turning Point](http://127.0.0.1:8765) or the [API reference](http://127.0.0.1:8765/docs).
To enable AI, start Ollama and run `ollama pull qwen2.5:1.5b`. Override the model or endpoint with
`TURNING_POINT_MODEL` or `TURNING_POINT_OLLAMA`. If the model is missing or returns invalid
evidence, the result is marked **evidence-only**. Suggested claims have a curated fallback;
custom claims without a valid model result are marked insufficient.

## Three-Minute Walkthrough

1. Open **Cricket** and investigate the suggested claim.
2. Open the citation for the required rate entering the last over. West Indies needed 19 from six legal balls.
3. Select **Make the opposing case**. Compare the verdicts and inspect the earlier scoring window.
4. Switch to **Formula 1** to compare pit-lane times, or **Adaptations** to compare openings without enabling the reveal.

## Design

FastAPI serves the case library, investigation API, and browser UI. Python computes sports facts
from pinned evidence; Ollama chooses bounded tools and classifies claims against their results.
The model can return fact IDs, not new evidence text. The server checks citations against the
current case and spoiler level. PostgreSQL stores the original and reviewed results separately,
including source version, model, tool names, and elapsed time.

The release is local-first: three curated cases, no live feeds, simulations, open uploads, or public
multi-user deployment. Prior DataForge code and migrations are retained for compatibility; its
upload endpoints are not mounted in Turning Point. The original sprint branches remain separate.

See [evidence sources and evaluation](docs/turning_point.md) and the
[contribution guide](docs/engineering/contribution_guide.md). The application code has no
declared license; third-party data and referenced works have separate terms.
