import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class Event(BaseModel):
    id: str
    label: str
    lane: str
    text: str
    level: int = 1
    value: float | None = None


class Fact(BaseModel):
    id: str
    text: str
    refs: list[str]
    level: int = 1


@dataclass(frozen=True)
class Case:
    id: str
    domain: str
    title: str
    subtitle: str
    claim: str
    source: str
    url: str
    limitations: str
    events: list[Event]
    tools: dict[str, list[Fact]]
    default_verdict: Literal["supported", "contradicted", "insufficient"]
    counter_tool: str
    source_revision: str = "1"
    links: tuple[tuple[str, str], ...] = ()

    @property
    def version(self) -> str:
        data = [self.source_revision, [e.model_dump() for e in self.events]]
        data += [{name: [f.model_dump() for f in facts] for name, facts in self.tools.items()}]
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

    def visible(self, level: int) -> list[Event]:
        return [event for event in self.events if event.level <= level]


def cricket_case() -> Case:
    raw = json.loads(Path(__file__).with_name("cricket.json").read_text(encoding="utf-8"))
    target = raw["target"]
    score = balls = wickets = 0
    events, wicket_events, overs = [], [], {}
    for i, (over, batter, bowler, runs, legal, lost) in enumerate(raw["deliveries"], 1):
        score += runs
        balls += legal
        wickets += lost
        remaining = max(0, 120 - balls)
        rate = (target - score) * 6 / remaining if remaining and score < target else None
        rate_text = f" Required rate: {rate:.2f}." if rate is not None else ""
        event = Event(
            id=f"ball-{i}",
            label=f"{over - 1}.{balls - (over - 1) * 6}" + ("" if legal else "+"),
            lane="West Indies chase",
            text=f"{batter} vs {bowler}: {runs} runs, {lost} wickets. "
            f"West Indies {score}/{wickets}; {remaining} legal balls left." + rate_text,
            value=rate,
        )
        events.append(event)
        overs[over] = (score, wickets, event.id)
        if lost:
            wicket_events.append(event.id)

    before, lost, anchor = overs[19]
    early, _, early_id = overs[15]
    finish, final_wickets, finish_id = overs[20]
    needed = target - before
    return Case(
        "eden-gardens-2016",
        "Cricket",
        "The final over",
        "West Indies vs England / 2016 T20 World Cup final",
        "England lost the match in the final over.",
        "Cricsheet / ODC Attribution 1.0",
        "https://cricsheet.org/matches/",
        "The score shows where the result changed, not whether a different bowling plan would "
        "have worked. Earlier overs also shaped the final equation.",
        events,
        {
            "required_rate": [
                Fact(
                    id="final-equation",
                    text=f"West Indies needed {needed} from six legal "
                    f"balls at {before}/{lost}, a required rate of {needed:.2f}.",
                    refs=[anchor],
                ),
                Fact(
                    id="finish",
                    text=f"The chase finished at {finish}/{final_wickets}, "
                    f"past the target of {target}.",
                    refs=[finish_id],
                ),
            ],
            "wickets": [
                Fact(
                    id="wicket-pressure",
                    text=f"England took {final_wickets} wickets; "
                    "those breakthroughs constrained the chase.",
                    refs=wicket_events,
                ),
            ],
            "scoring_windows": [
                Fact(
                    id="earlier-window",
                    text=f"West Indies scored {before - early} runs "
                    f"across overs 16-19, reaching {before} before the final over.",
                    refs=[early_id, anchor],
                ),
                Fact(
                    id="last-window",
                    text=f"West Indies scored {finish - before} in the "
                    "final over, turning the remaining target into a win.",
                    refs=[anchor, finish_id],
                ),
            ],
        },
        "supported",
        "scoring_windows",
        raw["source_sha256"],
    )


def monaco_case() -> Case:
    stops = [("Hamilton", 29, 23.783), ("Gasly", 30, 24.428), ("Vettel", 31, 24.369)]
    events = [
        Event(
            id=name.lower(),
            label=f"Lap {lap}",
            lane=name,
            text=f"{name} stopped on lap {lap}; recorded pit lane time {seconds:.3f} s.",
            value=seconds,
        )
        for name, lap, seconds in stops
    ] + [
        Event(
            id="rejoin",
            label="Lap 32",
            lane="Vettel / Gasly",
            text="Vettel rejoined narrowly ahead of Gasly and also ahead of Hamilton.",
        ),
        Event(
            id="finish",
            label="Finish",
            lane="Classification",
            text="Vettel P5, Gasly P6, Hamilton P7.",
        ),
    ]
    return Case(
        "monaco-2021",
        "Formula 1",
        "The Monaco overcut",
        "Vettel, Gasly and Hamilton / 2021 Monaco Grand Prix",
        "Vettel gained position by stopping later than Gasly and Hamilton.",
        "FIA classification and Aston Martin race recap",
        "https://www.fia.com/events/fia-formula-one-world-championship/season-2021/monaco-grand-prix/race-classification",
        "This snapshot has pit-lane durations, not full lap splits or interval traces. "
        "It cannot isolate tyre pace, exact gaps, counterfactuals, or team intent.",
        events,
        {
            "pit_window": [
                Fact(
                    id="stop-order",
                    text="Hamilton stopped on lap 29, Gasly on lap 30, and Vettel on lap 31.",
                    refs=["hamilton", "gasly", "vettel"],
                ),
                Fact(
                    id="overcut",
                    text="Vettel emerged ahead of both drivers and finished ahead of both.",
                    refs=["rejoin", "finish"],
                ),
            ],
            "compare_pit_times": [
                Fact(
                    id="not-stop-speed",
                    text=f"Vettel's pit-lane time was "
                    f"{stops[2][2] - stops[0][2]:.3f} seconds longer than Hamilton's. "
                    "The position gain was not a faster pit-lane transit.",
                    refs=["vettel", "hamilton"],
                ),
            ],
        },
        "supported",
        "compare_pit_times",
        links=(
            (
                "Aston Martin race recap",
                "https://www.astonmartinf1.com/en-GB/news/on-track/race-recap-double-points-finish-in-2021-monaco-gp",
            ),
        ),
    )


def adaptation_case() -> Case:
    return Case(
        "liore-reveal",
        "Adaptations",
        "Miracle or alchemy?",
        "Fullmetal Alchemist / Manga vs Brotherhood",
        "Brotherhood primes the audience to question Cornello's miracles earlier.",
        "Original scene annotations / VIZ and Crunchyroll references",
        "https://www.viz.com/manga-books/manga/fullmetal-alchemist-volume-1/product/399",
        "Scene order is observable. Audience expectations are an interpretation, "
        "not a measured viewer response.",
        [
            Event(
                id="manga-arrival",
                label="Chapter 1",
                lane="Manga",
                text="The manga opens in Liore, where Cornello's purported miracles "
                "frame the Elrics' first encounter with the town.",
            ),
            Event(
                id="anime-opening",
                label="Episode 1",
                lane="Brotherhood",
                text="The anime opens with a Central incident that showcases alchemy "
                "before the audience visits Liore.",
            ),
            Event(
                id="anime-liore",
                label="Episode 3",
                lane="Brotherhood",
                level=2,
                text="In Liore the brothers suspect Cornello is using a Philosopher's "
                "Stone to perform his apparent miracles.",
            ),
            Event(
                id="manga-explanation",
                label="Chapter 1",
                lane="Manga",
                level=2,
                text="The opening manga chapter also gives the Elrics reason to "
                "suspect that alchemy explains the apparent miracles.",
            ),
        ],
        {
            "clue_order": [
                Fact(
                    id="opening-order",
                    text="Brotherhood demonstrates alchemy in Central "
                    "before Liore; the manga puts Liore first.",
                    refs=["anime-opening", "manga-arrival"],
                ),
                Fact(
                    id="liore-context",
                    text="The anime brings the apparent miracles "
                    "and the Stone suspicion together in episode 3.",
                    refs=["anime-liore"],
                    level=2,
                ),
            ],
            "compare_clues": [
                Fact(
                    id="different-context",
                    text="Knowing how alchemy works is not the "
                    "same as knowing how Cornello's specific claim will be resolved.",
                    refs=["manga-arrival", "anime-opening"],
                ),
                Fact(
                    id="manga-suspicion",
                    text="The manga also gives readers an alchemical "
                    "explanation to consider within the opening chapter.",
                    refs=["manga-explanation"],
                    level=2,
                ),
            ],
        },
        "insufficient",
        "compare_clues",
        links=(
            ("Brotherhood episode 3", "https://www.crunchyroll.com/watch/G609Q9896/city-of-heresy"),
        ),
    )


CASES = {case.id: case for case in (cricket_case(), monaco_case(), adaptation_case())}
