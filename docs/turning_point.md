# Evidence and Evaluation

## Sources

- **Cricket:** [Cricsheet](https://cricsheet.org/matches/), ODC Attribution 1.0. Match 951373 from
  the [Men's T20 World Cup JSON archive](https://cricsheet.org/downloads/icc_mens_t20_world_cup_male_json.zip).
  The snapshot keeps the input hash and revision. Regenerate it using
  `python -m backend.turning_point.import_cricket <archive.zip>`. Delivery numbering tracks legal
  balls; a plus sign marks a wide or no-ball. Required rate is remaining runs times six divided by
  remaining legal balls, and is omitted after the target is met or when no legal balls remain.
- **Monaco:** a small, manually curated set of facts from the
  [FIA race classification](https://www.fia.com/events/fia-formula-one-world-championship/season-2021/monaco-grand-prix/race-classification)
  and [Aston Martin recap](https://www.astonmartinf1.com/en-GB/news/on-track/race-recap-double-points-finish-in-2021-monaco-gp).
  FastF1 exposes useful timing data, but no FastF1 feeds are bundled. The demo covers stop laps,
  transit times, and observed rejoin/finish order, not exact running gaps or full lap splits.
- **Adaptation:** original annotations referencing
  [VIZ volume 1](https://www.viz.com/manga-books/manga/fullmetal-alchemist-volume-1/product/399)
  and [Brotherhood episode 3](https://www.crunchyroll.com/watch/G609Q9896/city-of-heresy).
  No panels, subtitles, stills, or clips are bundled. Reveal notes are opt-in.

## Verification

```sh
alembic upgrade head
alembic check
python -m pytest -q
ruff check backend/turning_point tests/test_turning_point.py
ruff format --check backend/turning_point tests/test_turning_point.py
```

Check the browser module with `node --input-type=module --check < backend/turning_point/web/studio.js`
(in PowerShell, use `Get-Content -Raw backend/turning_point/web/studio.js | node --input-type=module --check`).

The first automated run passed 45 tests across Turning Point and the prior backend. Turning Point
checks the chase total and rate, persists a review linked to its original, resolves evidence IDs,
withholds a verdict for missing timing, rejects a hidden citation, and exercises a verdict revision
using a controlled model response. These results verify application behavior, not Ollama model
quality. Live model performance should be reported separately from controlled tests.

With Ollama installed and the model pulled, run `python -m backend.turning_point.evaluate`.
This emits per-case verdicts, citation scope, runtime, and tool traces. It exits nonzero for
incorrect reviewed verdicts or evidence-only results, so an offline run cannot pass as a model
evaluation. The local PostgreSQL smoke test completed all three investigations and challenges
in evidence-only mode. A live Ollama quality run was not completed.
